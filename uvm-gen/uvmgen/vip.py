"""Cadence VIP protocol knowledge: supported protocols, roles, and defaults.

The wrapper classes the generator emits are compile-clean UVM shells; the
class names below are *illustrative* Cadence VIP names used inside TODO(vip)
comments (exact names vary per VIP release — see $CDN_VIP_ROOT docs).
"""

PROTOCOLS = {
    "apb": {
        "title": "AMBA APB",
        "roles": ["master", "slave", "monitor"],
        "default_role": "master",
        "role_aliases": {},
        "knobs": [
            {"name": "addr_width", "sv_type": "int unsigned", "default": 32,
             "comment": "APB address bus width"},
            {"name": "data_width", "sv_type": "int unsigned", "default": 32,
             "comment": "APB data bus width"},
        ],
        "example_pkg": "denaliCdn_apbUvmPkg",
        "example_agent": "denaliCdn_apbUvmUserAgent",
        "example_cfg": "denaliCdn_apbUvmUserConfig",
    },
    "ahb": {
        "title": "AMBA AHB",
        "roles": ["master", "slave", "monitor"],
        "default_role": "master",
        "role_aliases": {},
        "knobs": [
            {"name": "addr_width", "sv_type": "int unsigned", "default": 32,
             "comment": "AHB address bus width"},
            {"name": "data_width", "sv_type": "int unsigned", "default": 32,
             "comment": "AHB data bus width"},
        ],
        "example_pkg": "denaliCdn_ahbUvmPkg",
        "example_agent": "denaliCdn_ahbUvmUserAgent",
        "example_cfg": "denaliCdn_ahbUvmUserConfig",
    },
    "i3c": {
        "title": "MIPI I3C",
        "roles": ["controller", "target", "monitor"],
        "default_role": "controller",
        # legacy terminology accepted and normalized
        "role_aliases": {"master": "controller", "slave": "target"},
        "knobs": [
            {"name": "ibi_enable", "sv_type": "bit", "default": 1,
             "comment": "In-Band Interrupt support (sensible default: enabled)"},
            {"name": "hot_join_enable", "sv_type": "bit", "default": 0,
             "comment": "Hot-Join support"},
            {"name": "static_addr", "sv_type": "bit [6:0]", "default": "7'h50",
             "comment": "static address (target role)"},
            {"name": "i3c_only_bus", "sv_type": "bit", "default": 1,
             "comment": "pure I3C bus (no legacy I2C devices present)"},
        ],
        "example_pkg": "denaliCdn_i3cUvmPkg",
        "example_agent": "denaliCdn_i3cUvmUserAgent",
        "example_cfg": "denaliCdn_i3cUvmUserConfig",
    },
}
