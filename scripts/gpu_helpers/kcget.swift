// kcget -- read secrets via the MODERN Security API, including iCloud-synced
// items that Passwords.app writes and the legacy `security` CLI cannot see.
//
// Why this exists: `security find-generic-password` uses the legacy SecKeychain*
// API, which only sees login.keychain-db / System.keychain. Items stored in
// Passwords.app live in the iCloud keychain and are invisible to it (rc=44).
//
// CRUCIAL: an item's human-visible name lives in kSecAttrLabel, NOT in
// kSecAttrService. Searching only service+account misses anything named in the
// GUI, so both are searched here, along with server and description.
//
//   kcget get  <name>        print the secret (matches service, label, or account)
//   kcget has  <name>        "present"/"missing"
//   kcget list [substr]      name + class + location of matching items (no secrets)
//   kcget dump               every item's identifying metadata (no secrets)

import Foundation
import Security

let classes: [(String, CFString)] = [
    ("generic ", kSecClassGenericPassword),
    ("internet", kSecClassInternetPassword),
]

/// Every identifying attribute of an item, so a name can be found wherever the
/// GUI happened to put it.
func ident(_ it: [String: Any]) -> [String] {
    var out: [String] = []
    let keys: [(String, CFString)] = [
        ("label", kSecAttrLabel),
        ("svce", kSecAttrService),
        ("acct", kSecAttrAccount),
        ("srvr", kSecAttrServer),
        ("desc", kSecAttrDescription),
    ]
    for (tag, k) in keys {
        if let v = it[k as String] as? String, !v.isEmpty { out.append("\(tag)=\(v)") }
    }
    return out
}

func allItems(cls: CFString) -> [[String: Any]] {
    let q: [String: Any] = [
        kSecClass as String: cls,
        kSecAttrSynchronizable as String: kSecAttrSynchronizableAny,
        kSecReturnAttributes as String: true,
        kSecMatchLimit as String: kSecMatchLimitAll,
    ]
    var out: CFTypeRef?
    guard SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess,
          let items = out as? [[String: Any]] else { return [] }
    return items
}

/// Fetch one item's secret. Tries service, then label -- an item named in the GUI
/// has an empty service, so a service-only query silently misses it.
func fetch(name: String) -> String? {
    for (_, cls) in classes {
        for key in [kSecAttrService, kSecAttrLabel, kSecAttrAccount] {
            let q: [String: Any] = [
                kSecClass as String: cls,
                kSecAttrSynchronizable as String: kSecAttrSynchronizableAny,
                kSecReturnData as String: true,
                kSecReturnAttributes as String: true,
                kSecMatchLimit as String: kSecMatchLimitOne,
                key as String: name,
            ]
            var out: CFTypeRef?
            if SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess,
               let d = out as? [String: Any],
               let data = d[kSecValueData as String] as? Data,
               let s = String(data: data, encoding: .utf8) {
                return s
            }
        }
    }
    return nil
}

let args = CommandLine.arguments
guard args.count >= 2 else {
    FileHandle.standardError.write("usage: kcget get|has|list|dump [name]\n".data(using: .utf8)!)
    exit(2)
}

switch args[1] {
case "get", "has":
    guard args.count >= 3 else { exit(2) }
    if let s = fetch(name: args[2]) {
        if args[1] == "get" { print(s, terminator: "") } else { print("present") }
        exit(0)
    }
    if args[1] == "has" { print("missing"); exit(1) }
    FileHandle.standardError.write("not found: \(args[2])\n".data(using: .utf8)!)
    exit(1)

case "list", "dump":
    let needle = (args.count > 2 && args[1] == "list") ? args[2].lowercased() : nil
    var shown = 0, total = 0
    for (label, cls) in classes {
        for it in allItems(cls: cls) {
            total += 1
            let parts = ident(it)
            let haystack = parts.joined(separator: " ").lowercased()
            if let nd = needle, !haystack.contains(nd) { continue }
            let sync = (it[kSecAttrSynchronizable as String] as? Bool) ?? false
            print("\(label) \(sync ? "icloud" : "local ") \(parts.joined(separator: "  "))")
            shown += 1
        }
    }
    FileHandle.standardError.write("\(shown) shown of \(total) total\n".data(using: .utf8)!)
    exit(0)

default:
    exit(2)
}
