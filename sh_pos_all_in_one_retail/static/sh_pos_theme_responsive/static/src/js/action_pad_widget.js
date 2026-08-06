odoo.define("sh_pos_all_in_one_retail._theme_action_pad_widget", function (require) {

    const ActionpadWidget = require("point_of_sale.ActionpadWidget");
    const Registries = require("point_of_sale.Registries");

    const PosActionpadWidget = (ActionpadWidget) =>
        class extends ActionpadWidget {
            super() {
                super.super()
            }
            sh_hide_numpad(event) {
                var self = this;
                $("div.numpad").slideToggle("slow", function () {
                    if ($('.slide_toggle_button').find('.fa')) {
                        if ($('.slide_toggle_button').find('.fa').hasClass('fa-chevron-down')) {
                            $('.slide_toggle_button').find('.fa').removeClass('fa-chevron-down')
                            $('.slide_toggle_button').find('.fa').addClass('fa-chevron-up')
                        }
                        else if ($('.slide_toggle_button').find('.fa').hasClass('fa-chevron-up')) {
                            $('.slide_toggle_button').find('.fa').removeClass('fa-chevron-up')
                            $('.slide_toggle_button').find('.fa').addClass('fa-chevron-down')
                        }
                    }
                });

            }
        };

    Registries.Component.extend(ActionpadWidget, PosActionpadWidget);

    return PosActionpadWidget

});
