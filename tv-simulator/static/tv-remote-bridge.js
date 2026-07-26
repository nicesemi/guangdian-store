/* TV Remote Bridge - Include this script in any app loaded inside the TV iframe */
(function() {
  var style = document.createElement('style');
  style.textContent = '.tv-focus-ring { outline: 3px solid #3b82f6 !important; outline-offset: 2px; box-shadow: 0 0 12px rgba(59,130,246,0.4) !important; transition: outline 0.15s, box-shadow 0.15s; }';
  document.head.appendChild(style);

  window.addEventListener('message', function(event) {
    var msg = event.data;
    if (!msg || msg.type !== 'tv-remote') return;

    switch(msg.action) {
      case 'input':
        var el = document.activeElement;
        var isInput = el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable);
        if (!isInput) {
          el = document.querySelector('input[type="text"], input:not([type]), textarea, [contenteditable="true"]');
        }
        if (el) {
          el.focus();
          if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
            var s = el.selectionStart, e = el.selectionEnd, v = el.value;
            el.value = v.substring(0, s) + msg.text + v.substring(e);
            el.selectionStart = el.selectionEnd = s + msg.text.length;
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
          } else {
            document.execCommand('insertText', false, msg.text);
          }
        }
        window.dispatchEvent(new CustomEvent('tv-input', {detail: {text: msg.text}}));
        break;

      case 'navigate':
        var focusables = Array.from(document.querySelectorAll(
          'a[href], button, input:not([type="hidden"]), select, textarea, [tabindex]:not([tabindex="-1"]), [contenteditable="true"]'
        )).filter(function(el) {
          var r = el.getBoundingClientRect();
          return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden';
        });

        if (focusables.length === 0) break;

        if (msg.direction === 'enter') {
          if (document.activeElement && document.activeElement.tagName === 'BUTTON') {
            document.activeElement.click();
          } else if (document.activeElement) {
            var form = document.activeElement.closest('form');
            if (form) form.dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}));
          }
          return;
        }

        if (msg.direction === 'back') {
          history.back();
          return;
        }

        var cur = focusables.indexOf(document.activeElement);
        var next = cur;
        if (msg.direction === 'down' || msg.direction === 'right') {
          next = cur < focusables.length - 1 ? cur + 1 : 0;
        } else if (msg.direction === 'up' || msg.direction === 'left') {
          next = cur > 0 ? cur - 1 : focusables.length - 1;
        }

        if (next !== cur && focusables[next]) {
          document.querySelectorAll('.tv-focus-ring').forEach(function(e) { e.classList.remove('tv-focus-ring'); });
          focusables[next].classList.add('tv-focus-ring');
          focusables[next].focus();
        }
        break;

      case 'voice':
        window.dispatchEvent(new CustomEvent('tv-voice-command', {detail: {text: msg.text}}));
        break;
    }
  });
})();
