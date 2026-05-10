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

  document.addEventListener("DOMContentLoaded", function () {
    initializeSettingsEditMode();
    initializeAutoSubmitControls();
  });
})();
