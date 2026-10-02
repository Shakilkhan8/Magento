/** @odoo-module */

import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useEffect } from "@odoo/owl";

class MagentoCollapseButtonKanbanController extends KanbanController {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        
        // Set up click handler for the toggle button using useEffect
        useEffect(() => {
            const button = document.getElementById('magento_button_toggle');
            if (!button) {
                return;
            }
            
            const debounce = (func, wait) => {
                let timeout;
                return function executedFunction(...args) {
                    const later = () => {
                        clearTimeout(timeout);
                        func(...args);
                    };
                    clearTimeout(timeout);
                    timeout = setTimeout(later, wait);
                };
            };
            
            const handleClick = debounce((ev) => {
                this._toggleBtn(ev);
            }, 300);
            
            button.addEventListener('click', handleClick);
            
            return () => {
                button.removeEventListener('click', handleClick);
            };
        });
    }

    /**
     * To toggle the OnBoarding button to hide /show the panel
     */
    async _toggleBtn(ev) {
        const companyId = parseInt(ev.currentTarget.getAttribute('data-company-id'));
        try {
            const result = await this.orm.call(
                'res.company',
                'action_toggle_magento_instances_onboarding_panel',
                [companyId]
            );
            
            const container = document.querySelector('.o_onboarding_container.collapse');
            const button = document.getElementById('magento_button_toggle');
            
            if (result === 'closed') {
                if (container) {
                    container.classList.remove('show');
                }
                if (button) {
                    button.innerHTML = 'Create more Magento instance';
                    button.style.backgroundColor = '#ececec';
                    button.style.border = '1px solid #ccc';
                }
            } else {
                if (container) {
                    container.classList.add('show');
                }
                if (button) {
                    button.innerHTML = 'Hide On boarding Panel';
                    button.style.backgroundColor = '';
                    button.style.border = '';
                }
            }
        } catch (error) {
            this.notification.add(_t('Warning'), {
                type: 'warning',
                message: _t('Something Went Wrong'),
            });
        }
    }
}

const MagentoOnBoardingToggleKanbanView = {
    ...kanbanView,
    Controller: MagentoCollapseButtonKanbanController,
};

registry.category("views").add("MagentoOnBoardingToggle", MagentoOnBoardingToggleKanbanView);
