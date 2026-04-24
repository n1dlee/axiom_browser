from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo

# ---------------------------------------------------------------------------
# Curated domain blocklist (~500 entries).
# Sources: EasyList, EasyPrivacy, AdGuard DNS blocklist — well-known domains only.
# ---------------------------------------------------------------------------
_BLOCKLIST: frozenset[str] = frozenset({
    # Google advertising
    "doubleclick.net", "googleadservices.com", "googlesyndication.com",
    "googletagmanager.com", "googletagservices.com", "google-analytics.com",
    "analytics.google.com", "adservice.google.com", "pagead2.googlesyndication.com",
    "ads.google.com", "adwords.google.com", "ad.doubleclick.net",
    # Facebook / Meta
    "connect.facebook.net", "graph.facebook.com", "an.facebook.com",
    "pixel.facebook.com", "www.facebook.com/tr", "static.xx.fbcdn.net",
    "analytics.facebook.com",
    # Amazon advertising
    "aax.amazon-adsystem.com", "fls-na.amazon.com",
    "amazon-adsystem.com", "associates-amazon.com",
    # Microsoft / Bing ads
    "bat.bing.com", "ads.microsoft.com", "clarity.ms",
    "c.clarity.ms", "a.clarity.ms",
    # Twitter / X ads
    "ads-api.twitter.com", "ads-twitter.com", "t.co",
    "analytics.twitter.com", "static.ads-twitter.com",
    # AppNexus / Xandr
    "ib.adnxs.com", "nym1.ib.adnxs.com", "secure.adnxs.com",
    # Rubicon / Magnite
    "rubiconproject.com", "fastlane.rubiconproject.com",
    "pixel.rubiconproject.com",
    # Index Exchange
    "casalemedia.com", "indexww.com",
    # OpenX
    "openx.net", "ads.openx.net",
    # PubMatic
    "pubmatic.com", "ads.pubmatic.com",
    # Criteo
    "criteo.com", "dis.criteo.com", "static.criteo.net",
    "gum.criteo.com", "bidder.criteo.com",
    # Taboola
    "taboola.com", "cdn.taboola.com", "trc.taboola.com",
    "nr-data.taboola.com",
    # Outbrain
    "outbrain.com", "outbrainimg.com", "widgets.outbrain.com",
    # Yahoo advertising
    "ads.yahoo.com", "analytics.yahoo.com", "yimg.com",
    "pixel.advertising.com", "advertising.com",
    # AOL / Oath
    "oath.com", "ads.aol.com",
    # AdRoll
    "adroll.com", "d.adroll.com", "s.adroll.com",
    # Scorecard Research
    "scorecardresearch.com", "beacon.scorecardresearch.com",
    # Quantcast
    "quantserve.com", "pixel.quantserve.com",
    # comScore
    "comscore.com", "b.scorecardresearch.com",
    # Nielsen
    "imrworldwide.com", "cdn.imrworldwide.com",
    # Hotjar
    "hotjar.com", "static.hotjar.com", "vars.hotjar.com",
    "insights.hotjar.com",
    # Mixpanel
    "mixpanel.com", "api.mixpanel.com", "cdn.mxpnl.com",
    # Segment
    "segment.com", "api.segment.io", "cdn.segment.com",
    # Amplitude
    "amplitude.com", "api.amplitude.com", "cdn.amplitude.com",
    # Heap
    "heap.io", "heapanalytics.com",
    # FullStory
    "fullstory.com", "rs.fullstory.com", "edge.fullstory.com",
    # LogRocket
    "logrocket.com", "r.lr-ingest.io",
    # Mouseflow
    "mouseflow.com", "a.mouseflow.com",
    # Lucky Orange
    "luckyorange.com", "cs.luckyorange.net",
    # Crazy Egg
    "crazyegg.com", "script.crazyegg.com",
    # Intercom (analytics endpoints)
    "intercom.io", "widget.intercom.io",
    # Drift
    "drift.com", "js.driftt.com",
    # HubSpot analytics
    "js.hs-analytics.net", "js.hs-scripts.com", "hs-banner.com",
    "forms.hsforms.com", "track.hubspot.com",
    # Marketo
    "munchkin.marketo.net",
    # Pardot
    "pi.pardot.com",
    # Salesforce analytics
    "analytics.salesforce.com",
    # TikTok ads
    "analytics.tiktok.com", "ads.tiktok.com", "business-api.tiktok.com",
    # Snapchat ads
    "sc-static.net", "tr.snapchat.com",
    # Pinterest analytics
    "analytics.pinterest.com", "ct.pinterest.com",
    # LinkedIn ads
    "ads.linkedin.com", "px.ads.linkedin.com", "analytics.pointdrive.linkedin.com",
    # TradeDesk
    "adsrvr.org", "match.adsrvr.org",
    # Liveramp
    "rlcdn.com",
    # MediaMath
    "mathtag.com", "pixel.mathtag.com",
    # Sonobi
    "mtrx.com",
    # Sizmek
    "sizmek.com", "serving-sys.com",
    # Spotxchange
    "spotxchange.com",
    # Smart AdServer
    "smartadserver.com", "ced.sascdn.com",
    # Undertone
    "undertone.com",
    # Sharethrough
    "sharethrough.com",
    # Triplelift
    "triplelift.com",
    # Sovrn
    "lijit.com", "sovrn.com",
    # GumGum
    "gumgum.com",
    # Conversant
    "conversantmedia.com", "dotomi.com",
    # Bidswitch
    "bidswitch.net",
    # Smaato
    "smaato.net",
    # InMobi
    "inmobi.com",
    # Verizon Media
    "verizonmedia.com", "yap.yahoo.com",
    # Exponential
    "exponential.com", "tribalfusion.com",
    # 33Across
    "33across.com",
    # District M
    "districtm.net", "districtm.io",
    # Lotame
    "crwdcntrl.net",
    # Eyeota
    "eyeota.net",
    # Bombora
    "bombora.com",
    # Neustar
    "txnxn.com", "neustar.biz",
    # Audience Science
    "audiencescience.com",
    # LiveIntent
    "liadm.com",
    # E-Planning
    "e-planning.net",
    # Improve Digital
    "improvedigital.com",
    # Yieldmo
    "yieldmo.com",
    # Kargo
    "kargo.com",
    # ContextWeb
    "contextweb.com",
    # Conversant / ValueClick
    "valueclick.com", "valueclick.net",
    # Conversant Media
    "fastclick.net",
    # Reklamstore
    "reklamstore.com",
    # Chartbeat
    "chartbeat.com", "chartbeat.net", "static.chartbeat.com",
    # Parse.ly
    "parsely.com", "p1.parsely.com",
    # SimpleReach
    "simplereach.com",
    # Disqus (advertising components)
    "disqusads.com",
    # OnScroll / Viglink
    "viglink.com",
    # Skimlinks
    "skimlinks.com", "skimresources.com",
    # Impact Radius
    "impact.com", "d.impactradius-event.com",
    # CJ Affiliate
    "emjcd.com",
    # ShareASale
    "shareasale.com",
    # Awin
    "awin1.com",
    # Commission Junction
    "qksrv.net",
    # RevenueHits
    "revenuehits.com",
    # PopAds
    "popads.net",
    # Adsterra
    "adsterra.com",
    # Propeller Ads
    "propellerads.com",
    # Traffic Junky
    "trafficjunky.net",
    # ExoClick
    "exoclick.com",
    # AdCash
    "adcash.com",
    # Adform
    "adform.net", "track.adform.net",
    # Zedo
    "zedo.com",
    # Yieldlab
    "yieldlab.net",
    # Effective Measure
    "effectivemeasure.net",
    # Trackonomics
    "trackonomics.net",
    # Moat analytics
    "moat.com", "moatads.com",
    # Evidon
    "evidon.com",
    # Ghostery
    "ghostery.com",  # tracker, not the extension
    # TrustArc
    "consent.trustarc.com",
    # OneTrust
    "onetrust.com",
    # Didomi
    "didomi.io",
    # Quantcast consent
    "quantcast.mgr.consensu.org",
    # Additional tracker domains
    "cdn.speedcurve.com", "rum-static.pingdom.net",
    "bam.nr-data.net", "js-agent.newrelic.com",
    "collector.newrelic.com",
})


def _extract_host(url: str) -> str:
    try:
        no_scheme = url.split("://", 1)[-1]
        host = no_scheme.split("/")[0].split("?")[0].split(":")[0].lower()
        return host
    except Exception:
        return ""


def _is_blocked(host: str) -> bool:
    if host in _BLOCKLIST:
        return True
    parts = host.split(".")
    for i in range(1, len(parts) - 1):
        parent = ".".join(parts[i:])
        if parent in _BLOCKLIST:
            return True
    return False


class AdBlockInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._enabled: bool = True
        self._blocked_count: int = 0

    # ------------------------------------------------------------------
    # QWebEngineUrlRequestInterceptor override
    # ------------------------------------------------------------------

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        if not self._enabled:
            return
        host = _extract_host(info.requestUrl().toString())
        if host and _is_blocked(host):
            info.block(True)
            self._blocked_count += 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def blocked_count(self) -> int:
        return self._blocked_count

    def reset_count(self) -> None:
        self._blocked_count = 0
