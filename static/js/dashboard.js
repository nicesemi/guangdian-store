/** 管理后台 - 实时数据 */
(function() {
  'use strict';

  // 刷新节点状态
  async function refreshNodeStats() {
    try {
      const res = await fetch('/api/stats');
      const data = await res.json();
      if (document.getElementById('stat-total-tops')) {
        document.getElementById('stat-total-tops').textContent = (data.total_tops / 1024).toFixed(1);
      }
      if (document.getElementById('stat-online-nodes')) {
        document.getElementById('stat-online-nodes').textContent = data.online_nodes;
      }
      if (document.getElementById('stat-active-tasks')) {
        document.getElementById('stat-active-tasks').textContent = data.active_tasks;
      }
    } catch (e) {
      console.error('Failed to refresh stats:', e);
    }
  }

  // 每10秒自动刷新
  if (document.querySelector('.stats-grid')) {
    refreshNodeStats();
    setInterval(refreshNodeStats, 10000);
  }

  // TOPS利用率图表动画（CSS bar chart）
  function animateBars() {
    document.querySelectorAll('.bar-fill').forEach(function(bar) {
      var target = bar.getAttribute('data-height') || '0';
      bar.style.height = target + '%';
    });
  }

  if (document.querySelector('.bar-chart')) {
    setTimeout(animateBars, 300);
  }

  // 实时时钟
  function updateClock(elId) {
    var el = document.getElementById(elId);
    if (!el) return;
    var now = new Date();
    el.textContent = now.toLocaleTimeString('zh-CN', { hour12: false });
  }

  if (document.getElementById('tv-clock')) {
    updateClock('tv-clock');
    setInterval(function() { updateClock('tv-clock'); }, 1000);
  }
})();
