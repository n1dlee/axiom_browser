import os
from typing import Optional, TYPE_CHECKING

from PyQt6.QtWebEngineCore import (
    QWebEngineProfile, QWebEngineSettings,
    QWebEngineUrlRequestInterceptor, QWebEngineScript,
)


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

    def initialize(self, interceptor: Optional[QWebEngineUrlRequestInterceptor] = None) -> QWebEngineProfile:
        if self._initialized:
            return self._profile  # type: ignore[return-value]

        storage_path = _profile_storage_path()
        os.makedirs(storage_path, exist_ok=True)

        self._profile = QWebEngineProfile("axiom_default")
        self._profile.setPersistentStoragePath(storage_path)
        self._profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )

        settings = self._profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript, True)

        if interceptor is not None:
            self._profile.setUrlRequestInterceptor(interceptor)

        self._inject_passkey_block()

        self._initialized = True
        return self._profile

    def _inject_passkey_block(self) -> None:
        """Inject a script that silently refuses WebAuthn / passkey prompts."""
        js = """
(function () {
    'use strict';
    var _blocked = function () {
        return Promise.reject(
            new DOMException('Passkeys are disabled in AXIOM.', 'NotAllowedError')
        );
    };
    try {
        Object.defineProperty(navigator, 'credentials', {
            configurable: false,
            enumerable: true,
            value: Object.freeze({
                get: _blocked,
                create: _blocked,
                store: _blocked,
                preventSilentAccess: function () { return Promise.resolve(); }
            })
        });
    } catch (_) {}
})();
"""
        script = QWebEngineScript()
        script.setName("axiom_passkey_block")
        script.setSourceCode(js)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(False)
        self._profile.scripts().insert(script)

    @property
    def profile(self) -> QWebEngineProfile:
        if not self._initialized or self._profile is None:
            raise RuntimeError("BrowserEngine.initialize() must be called before accessing profile")
        return self._profile

    def set_download_path(self, path: str) -> None:
        self.profile.setDownloadPath(path)
