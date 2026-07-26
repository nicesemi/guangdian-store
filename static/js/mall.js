/** 商城交互 */
(function() {
  'use strict';

  // 安装Skill
  document.querySelectorAll('.btn-install').forEach(function(btn) {
    btn.addEventListener('click', async function() {
      var skillId = this.getAttribute('data-skill-id');
      if (!skillId) return;

      this.disabled = true;
      this.textContent = '安装中...';

      try {
        var res = await fetch('/api/skills/' + skillId + '/install', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        var data = await res.json();

        if (res.ok) {
          this.textContent = '已安装';
          this.className = 'btn btn-success btn-sm';
          this.disabled = true;
          if (data.message) {
            // 刷新页面或更新UI
          }
        } else {
          this.disabled = false;
          this.textContent = '安装';
          alert(data.detail || '安装失败');
        }
      } catch (e) {
        this.disabled = false;
        this.textContent = '安装';
        console.error(e);
      }
    });
  });

  // 卸载Skill
  document.querySelectorAll('.btn-uninstall').forEach(function(btn) {
    btn.addEventListener('click', async function() {
      var skillId = this.getAttribute('data-skill-id');
      if (!skillId) return;
      if (!confirm('确定要卸载该Skill吗？')) return;

      this.disabled = true;
      this.textContent = '卸载中...';

      try {
        var res = await fetch('/api/skills/' + skillId + '/uninstall', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        var data = await res.json();

        if (res.ok) {
          var card = this.closest('.skill-card');
          if (card) card.remove();
          if (data.message) alert(data.message);
        } else {
          this.disabled = false;
          this.textContent = '卸载';
          alert(data.detail || '卸载失败');
        }
      } catch (e) {
        this.disabled = false;
        this.textContent = '卸载';
        console.error(e);
      }
    });
  });
})();
