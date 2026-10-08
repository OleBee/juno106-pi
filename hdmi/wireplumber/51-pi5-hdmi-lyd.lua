-- /etc/wireplumber/main.lua.d/51-pi5-hdmi-lyd.lua  (bare for WirePlumber 0.4, Pi OS Bookworm)
-- Samme regler som 51-pi5-hdmi-lyd.conf for 0.5.
local function regel(moenster, kortnavn, props)
  table.insert(alsa_monitor.rules, {
    matches = {
      { { "node.name", "matches", moenster } },
      { { "alsa.card_name", "equals", kortnavn }, { "media.class", "equals", "Audio/Sink" } },
    },
    apply_properties = props,
  })
end

regel("alsa_output.platform-107c701400.hdmi.*", "vc4-hdmi-0", {
  ["node.description"] = "HDMI0 (primær, ved USB-C)",
  ["priority.session"] = 2000, ["priority.driver"] = 2000,
  ["audio.rate"] = 48000,
  ["api.alsa.period-size"] = 256, ["api.alsa.headroom"] = 256,
  ["session.suspend-timeout-seconds"] = 0,
})
regel("alsa_output.platform-107c706400.hdmi.*", "vc4-hdmi-1", {
  ["node.description"] = "HDMI1 (reserve)",
  ["priority.session"] = 1500, ["priority.driver"] = 1500,
  ["audio.rate"] = 48000,
  ["api.alsa.period-size"] = 256, ["api.alsa.headroom"] = 256,
  ["session.suspend-timeout-seconds"] = 0,
})
table.insert(alsa_monitor.rules, {
  matches = { { { "node.name", "matches", "alsa_output.usb-*" } } },
  apply_properties = {
    ["priority.session"] = 1000, ["priority.driver"] = 1000,
    ["api.alsa.period-size"] = 128, ["api.alsa.headroom"] = 0,
  },
})
