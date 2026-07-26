/** 电视端交互 */
(function() {
  'use strict';

  var focusIndex = 0;
  var cards = document.querySelectorAll('.tv-card');

  function setFocus(idx) {
    cards.forEach(function(c, i) {
      c.classList.toggle('focused', i === idx);
    });
  }

  // 键盘导航（模拟遥控器方向键）
  document.addEventListener('keydown', function(e) {
    if (!cards.length) return;
    var cols = 4;
    var row = Math.floor(focusIndex / cols);
    var col = focusIndex % cols;
    var totalRows = Math.ceil(cards.length / cols);

    switch (e.key) {
      case 'ArrowUp':
        e.preventDefault();
        row = Math.max(0, row - 1);
        break;
      case 'ArrowDown':
        e.preventDefault();
        row = Math.min(totalRows - 1, row + 1);
        break;
      case 'ArrowLeft':
        e.preventDefault();
        col = Math.max(0, col - 1);
        break;
      case 'ArrowRight':
        e.preventDefault();
        col = Math.min(cols - 1, col + 1);
        break;
      case 'Enter':
        e.preventDefault();
        var link = cards[focusIndex].querySelector('a');
        if (link) link.click();
        return;
      default:
        return;
    }

    // 确保不超出卡片总数
    var newIdx = row * cols + col;
    if (newIdx >= cards.length) newIdx = focusIndex;
    if (newIdx < 0) newIdx = 0;

    focusIndex = newIdx;
    setFocus(focusIndex);
  });

  // 初始焦点
  if (cards.length) {
    setFocus(0);
  }

  // 语音搜索（演示）
  var voiceBtn = document.getElementById('voice-search-btn');
  if (voiceBtn) {
    voiceBtn.addEventListener('click', function() {
      alert('语音搜索功能演示：请说出您要搜索的内容');
    });
  }
})();
