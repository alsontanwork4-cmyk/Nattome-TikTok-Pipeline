(function () {
  function initializeSettingsEditMode() {
    var panel = document.getElementById("unified-settings-panel");
    if (!panel) return;

    var btn = document.getElementById("edit-toggle-btn");
    var hint = document.getElementById("settings-mode-hint");
    var toggles = document.querySelectorAll("[data-settings-edit-toggle]");

    panel.classList.add("readonly-mode");
    panel.classList.remove("edit-mode");
    setFieldsReadonly(panel, true);

    window.toggleSettingsEdit = function () {
      var isReadonly = panel.classList.contains("readonly-mode");
      if (isReadonly) {
        panel.classList.remove("readonly-mode");
        panel.classList.add("edit-mode");
        if (btn) {
          btn.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg> Cancel';
          btn.classList.add("cancel-state");
        }
        if (hint) hint.textContent = "Editing mode - make your changes and save below.";
        setFieldsReadonly(panel, false);
      } else {
        panel.classList.add("readonly-mode");
        panel.classList.remove("edit-mode");
        if (btn) {
          btn.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Edit Settings';
          btn.classList.remove("cancel-state");
        }
        if (hint) hint.textContent = "Viewing current settings. Click Edit to make changes.";
        setFieldsReadonly(panel, true);
        var form = panel.querySelector(".settings-form");
        if (form) form.reset();
      }
    };

    for (var i = 0; i < toggles.length; i++) {
      toggles[i].addEventListener("click", window.toggleSettingsEdit);
    }
  }

  function setFieldsReadonly(panel, readonly) {
    var inputs = panel.querySelectorAll('.settings-form input[type="text"], .settings-form textarea');
    var selects = panel.querySelectorAll(".settings-form select");
    var checkboxes = panel.querySelectorAll('.settings-form input[type="checkbox"]');

    for (var i = 0; i < inputs.length; i++) {
      if (inputs[i].name === "reason") continue;
      inputs[i].readOnly = readonly;
      if (readonly) {
        inputs[i].tabIndex = -1;
      } else {
        inputs[i].removeAttribute("tabindex");
      }
    }
    for (var j = 0; j < selects.length; j++) {
      selects[j].disabled = readonly;
    }
    for (var k = 0; k < checkboxes.length; k++) {
      checkboxes[k].disabled = readonly;
    }
  }

  function initializeAutoSubmitControls() {
    var controls = document.querySelectorAll("[data-auto-submit]");
    for (var i = 0; i < controls.length; i++) {
      controls[i].addEventListener("change", function () {
        if (this.form) this.form.submit();
      });
    }
  }

  function initializeAgentAutoRefresh() {
    var marker = document.querySelector("[data-agent-auto-refresh]");
    if (!marker) return;
    var seconds = parseInt(marker.getAttribute("data-agent-auto-refresh"), 10);
    if (!seconds || seconds < 5) seconds = 5;
    window.setTimeout(function () {
      window.location.reload();
    }, seconds * 1000);
  }

  function initializeAgentCardEditMode() {
    var forms = document.querySelectorAll("[data-card-form]");
    for (var i = 0; i < forms.length; i++) {
      setupCardForm(forms[i]);
    }
  }

  function setupCardForm(form) {
    var editBtn = form.querySelector("[data-card-edit]");
    var cancelBtn = form.querySelector("[data-card-cancel]");
    var saveBtn = form.querySelector("[data-card-save]");
    if (!editBtn || !cancelBtn || !saveBtn) return;

    function applyMode(mode) {
      form.setAttribute("data-edit-mode", mode);
      var editing = mode === "on";
      var onSettingsTab = form.getAttribute("data-active-tab") !== "logs";
      setCardFieldsReadonly(form, !editing);
      editBtn.hidden = editing || !onSettingsTab;
      cancelBtn.hidden = !editing || !onSettingsTab;
      saveBtn.hidden = !editing || !onSettingsTab;
    }

    applyMode("off");

    editBtn.addEventListener("click", function () {
      applyMode("on");
      var firstField = form.querySelector("input:not([type='hidden']):not([disabled]), textarea:not([disabled]), select:not([disabled])");
      if (firstField) {
        try { firstField.focus(); } catch (e) {}
      }
    });

    cancelBtn.addEventListener("click", function () {
      form.reset();
      applyMode("off");
    });

    var tabs = form.querySelectorAll("[data-card-tab]");
    var panes = form.querySelectorAll("[data-card-pane]");
    function activateTab(name) {
      form.setAttribute("data-active-tab", name);
      for (var t = 0; t < tabs.length; t++) {
        var match = tabs[t].getAttribute("data-card-tab") === name;
        tabs[t].setAttribute("aria-selected", match ? "true" : "false");
      }
      for (var p = 0; p < panes.length; p++) {
        panes[p].hidden = panes[p].getAttribute("data-card-pane") !== name;
      }
      applyMode(form.getAttribute("data-edit-mode") || "off");
    }
    for (var i = 0; i < tabs.length; i++) {
      (function (tab) {
        tab.addEventListener("click", function () {
          activateTab(tab.getAttribute("data-card-tab"));
        });
      })(tabs[i]);
    }
  }

  function setCardFieldsReadonly(form, readonly) {
    var inputs = form.querySelectorAll("input[type='text'], textarea");
    for (var i = 0; i < inputs.length; i++) {
      if (inputs[i].hasAttribute("data-always-readonly")) {
        inputs[i].readOnly = true;
        continue;
      }
      inputs[i].readOnly = readonly;
    }
    var checkboxes = form.querySelectorAll("input[type='checkbox']");
    for (var j = 0; j < checkboxes.length; j++) {
      checkboxes[j].disabled = readonly;
    }
    var selects = form.querySelectorAll("select");
    for (var k = 0; k < selects.length; k++) {
      selects[k].disabled = readonly;
    }
  }

  function initializeSidebarToggle() {
    var btn = document.getElementById("sidebar-toggle");
    if (!btn) return;
    var root = document.documentElement;
    function syncAria() {
      btn.setAttribute("aria-expanded", root.dataset.sidebar === "collapsed" ? "false" : "true");
    }
    syncAria();
    btn.addEventListener("click", function () {
      var collapsed = root.dataset.sidebar === "collapsed";
      if (collapsed) {
        delete root.dataset.sidebar;
        try { localStorage.setItem("nattome.sidebarCollapsed", "0"); } catch (e) {}
      } else {
        root.dataset.sidebar = "collapsed";
        try { localStorage.setItem("nattome.sidebarCollapsed", "1"); } catch (e) {}
      }
      syncAria();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initializeSettingsEditMode();
    initializeAutoSubmitControls();
    initializeAgentAutoRefresh();
    initializeSidebarToggle();
    initializeAgentCardEditMode();
  });
})();
