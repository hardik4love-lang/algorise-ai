/**
 * Global JavaScript - Disable Select2 Everywhere, Use Native Dropdowns
 */

(function() {
    'use strict';

    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        disableSelect2Globally();
    });

    // Also initialize when jQuery is ready (for compatibility)
    if (typeof jQuery !== 'undefined') {
        jQuery(document).ready(function() {
            disableSelect2Globally();
        });
    }

    function disableSelect2Globally() {
        if (typeof jQuery !== 'undefined' && jQuery.fn.select2) {
            console.log('Disabling select2 globally - using native dropdowns');
            
            // Destroy any existing select2 instances
            jQuery('.select2-hidden-accessible').each(function() {
                try {
                    jQuery(this).select2('destroy');
                    console.log('Destroyed select2 instance');
                } catch(e) {
                    console.log('Could not destroy select2:', e);
                }
            });
            
            // Prevent select2 from initializing anywhere
            const originalSelect2 = jQuery.fn.select2;
            jQuery.fn.select2 = function(options) {
                // Always return the element without initializing select2
                console.log('Select2 initialization blocked - using native dropdown');
                return this;
            };
        }

        // Prevent zoom on input focus for iOS
        const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        if (isTouchDevice && /iPhone|iPad|iPod/.test(navigator.userAgent)) {
            const inputs = document.querySelectorAll('input, select, textarea');
            inputs.forEach(function(input) {
                const fontSize = window.getComputedStyle(input).fontSize;
                if (parseFloat(fontSize) < 16) {
                    input.style.fontSize = '16px';
                }
            });
        }
    }

    // Export for manual initialization if needed
    window.disableSelect2Globally = disableSelect2Globally;
})();
