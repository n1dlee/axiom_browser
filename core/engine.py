import logging
import os
from typing import Optional

from PyQt6.QtWebEngineCore import (
    QWebEngineProfile, QWebEngineSettings,
    QWebEngineUrlRequestInterceptor, QWebEngineScript,
)

_log = logging.getLogger(__name__)


def _profile_storage_path() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "Axiom", "profile")


class BrowserEngine:
    _instance: Optional["BrowserEngine"] = None

    def __new__(cls) -> "BrowserEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._profile = None
            cls._instance._initialized = False
        return cls._instance

    def initialize(
        self,
        interceptor: Optional[QWebEngineUrlRequestInterceptor] = None,
    ) -> QWebEngineProfile:
        if self._initialized:
            return self._profile  # type: ignore[return-value]

        storage_path = _profile_storage_path()
        os.makedirs(storage_path, exist_ok=True)

        self._profile = QWebEngineProfile("axiom_default")
        self._profile.setPersistentStoragePath(storage_path)
        self._profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )

        self._apply_settings()

        if interceptor is not None:
            self._profile.setUrlRequestInterceptor(interceptor)

        self._inject_passkey_block()

        self._initialized = True
        return self._profile

    def _apply_settings(self) -> None:
        """Apply web-engine attribute defaults.

        Security rationale for non-obvious choices
        -------------------------------------------
        JavascriptCanOpenWindows — kept True because AXIOM routes all
            createWindow() calls through _AxiomPage.createWindow(), which
            hands them to the tab manager.  Disabling this would break
            target="_blank" links and window.open() entirely.

        AllowWindowActivationFromJavaScript — False by default.  Focus-
            stealing is a well-known abuse vector (fake login prompts, etc.).
            Sites that legitimately need it are rare; if one breaks the user
            can reload without losing anything.

        These two are the most security-relevant defaults.  Everything else
        (WebGL, LocalStorage, FullScreen, ScrollAnimator) has no meaningful
        security surface and is enabled for web-compat.
        """
        s = self._profile.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled,              True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled,            True)
        s.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled,                   True)
        s.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled,       True)
        s.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled,          True)

        # Required for createWindow() routing — see rationale above.
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,       True)

        # Disabled: focus-stealing is an abuse vector with negligible legit use.
        s.setAttribute(QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript, False)

    def _inject_passkey_block(self) -> None:
        """Silently refuse WebAuthn / passkey credential API calls.

        Why MainWorld?
        --------------
        ``navigator.credentials`` lives in the page's main JavaScript context.
        To replace it we *must* inject into MainWorld — an IsolatedWorld cannot
        shadow a main-world property.  The trade-off is accepted and documented
        here so future maintainers don't move this to ApplicationWorld thinking
        it is safer (it would simply have no effect).

        The script also emits a non-blocking console.debug message for local
        telemetry so devs can verify the override is active without noise in
        production pages.
        """
        js = """
(function () {
    'use strict';
    var _blocked = function (op) {
        console.debug('[AXIOM] navigator.credentials.' + op + '() blocked.');
        return Promise.reject(
            new DOMException('Passkeys are disabled in AXIOM.', 'NotAllowedError')
        );
    };
    try {
        Object.defineProperty(navigator, 'credentials', {
            configurable: false,
            enumerable:   true,
            value: Object.freeze({
                get:                 function () { return _blocked('get');    },
                create:              function () { return _blocked('create'); },
                store:               function () { return _blocked('store');  },
                preventSilentAccess: function () { return Promise.resolve(); }
            })
        });
    } catch (_) {
        // Already defined (e.g. same profile reused in tests) — ignore.
    }
})();
"""
        script = QWebEngineScript()
        script.setName("axiom_passkey_block")
        script.setSourceCode(js)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        # Must be MainWorld — see docstring above.
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(False)
        self._profile.scripts().insert(script)
        _log.debug("Passkey-block script injected into MainWorld.")

    @property
    def profile(self) -> QWebEngineProfile:
        if not self._initialized or self._profile is None:
            raise RuntimeError(
                "BrowserEngine.initialize() must be called before accessing profile"
            )
        return self._profile

    def set_download_path(self, path: str) -> None:
        self.profile.setDownloadPath(path)
