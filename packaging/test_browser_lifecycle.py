"""Node lifecycle UI regression; all dispatch is isolated and mocked."""
from contextlib import ExitStack
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from playwright.sync_api import expect, sync_playwright
from test_browser_console import listener, server, load_config, save_config


def run():
    with ExitStack() as stack:
        directory = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='npt-lifecycle-ui-')))
        stack.enter_context(patch.dict(os.environ, NET_PROXY_CONFIG=str(directory / 'config.json')))
        config = load_config()
        config.update(gateways=[dict(id='g', name='fixture gateway', host='192.0.2.183', port=7890)],
                      active_gateway_id='g', clients=[])
        for index, state in enumerate(('enabled', 'disabled', 'unknown')):
            config['clients'].append(dict(id='node-' + state, name='fixture ' + state,
                host='node.invalid', port=2200 + index, ssh_user='tester', access_mode='ssh',
                auth_type='key', bound_gateway_id='g', node_revision=0, identity_version=1,
                lifecycle_version=1, managed_state=state, is_proxy_enabled=state == 'enabled',
                verification={'verified': state != 'unknown', 'status': state,
                    'restored_environment': {'observed': True, 'proxy_present': True,
                        'matched_gateway': {'id': 'g', 'host': '192.0.2.183', 'port': 7890}}}))
        save_config(config)
        console = stack.enter_context(listener(server.ProxyConsoleHandler))
        playwright = stack.enter_context(sync_playwright())
        browser = playwright.chromium.launch()
        stack.callback(browser.close)
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        errors, dialogs, mutations = [], [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.accept()))
        page.goto('http://127.0.0.1:' + str(console.server_port))
        page.locator('[data-tab="tab-topology"]').click()
        table = page.locator('#top-clients-tbody')
        expect(table).to_contain_text('已核验开启')
        expect(table).to_contain_text('已核验恢复')
        expect(table).to_contain_text('未核验')
        expect(table).to_contain_text('192.0.2.183:7890')

        def dispatch(target, action, config):
            mutations.append((target['id'], action))
            return {'returncode': 0, 'managed_state': 'enabled' if action == 'on' else 'disabled',
                    'verification': {'verified': True, 'status': 'enabled' if action == 'on' else 'restored'}}

        # Filtering produces an explicit immutable selection, never an implicit all-nodes operation.
        page.locator('#node-search-input').fill('fixture unknown')
        with patch.object(server, 'apply_node_proxy', side_effect=dispatch):
            page.locator('#top-enable-all-btn').click()
            expect(page.locator('#top-enable-all-btn')).to_be_enabled()
        assert mutations == [('node-unknown', 'on')], mutations
        assert any('1 个节点' in message for message in dialogs), dialogs
        page.locator('#node-search-input').fill('')

        # Failed cleanup keeps the row registered and refreshes its revision/state.
        row = table.locator('tr', has=page.locator('[data-action="delete-client"][data-id="node-enabled"]'))
        row.locator('.btn-dropdown-toggle').click()
        with patch.object(server, 'apply_node_proxy', return_value={
                'returncode': 1, 'managed_state': 'unknown', 'error': 'fixture restoration unknown'}):
            with page.expect_event('dialog', predicate=lambda dialog: 'fixture restoration unknown' in dialog.message):
                row.locator('[data-action="delete-client"]').click()
            expect(table).to_contain_text('fixture enabled')
            expect(page.locator('#node-stats-badge')).to_contain_text('未核验')
        assert any('fixture restoration unknown' in message for message in dialogs), dialogs
        assert any(item['id'] == 'node-enabled' for item in load_config()['clients'])

        # A stale editor cannot overwrite changes made by another page.
        row.locator('.btn-dropdown-toggle').click()
        row.locator('[data-action="edit-client"]').click()
        page.locator('#form-client-name').fill('stale UI edit')
        latest = load_config()
        latest['clients'][0]['node_revision'] += 1
        latest['clients'][0]['name'] = 'concurrent edit'
        save_config(latest)
        page.locator('#modal-client-save-btn').click()
        expect(page.locator('#form-client-hint')).to_contain_text('记录已变化')
        assert load_config()['clients'][0]['name'] == 'concurrent edit'
        page.locator('#modal-client-close').click()

        # Explicit local mode is usable without hidden SSH form fields.
        page.locator('#top-add-client-btn').click()
        page.locator('#form-client-name').fill('controller local')
        page.locator('#form-client-access-mode').select_option('local')
        page.locator('#modal-client-save-btn').click()
        expect(page.locator('#modal-client')).to_be_hidden()
        added = next(item for item in load_config()['clients'] if item['name'] == 'controller local')
        assert added['access_mode'] == 'local' and added['host'] == 'localhost'
        assert 'ssh_pass' not in added

        for width in (1280, 390):
            page.set_viewport_size({'width': width, 'height': 900})
            assert page.evaluate('document.documentElement.scrollWidth') <= width
        assert not errors, errors


if __name__ == '__main__':
    run()
    print('Isolated node lifecycle browser checks passed.')
