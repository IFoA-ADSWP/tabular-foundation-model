// kcget -- read secrets via the MODERN Security API, including iCloud-synced
// items that Passwords.app writes and the legacy `security` CLI cannot see.
//
// Why this exists: `security find-generic-password` uses the legacy SecKeychain*
// API, which only sees login.keychain-db / System.keychain. Items stored in
// Passwords.app live in the iCloud keychain and are invisible to it (rc=44).
// SecItemCopyMatching with kSecAttrSynchronizable=Any reaches both.
//
//   kcget get  <service> [account]   print the secret
//   kcget has  <service> [account]   "present"/"missing"
//   kcget list [substr]              service/account of matching items (no secrets)

import Foundation
import Security

func query(service: String?, account: String?, all: Bool) -> [String: Any] {
    var q: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrSynchronizable as String: kSecAttrSynchronizableAny,
        kSecReturnAttributes as String: true,
        kSecMatchLimit as String: all ? kSecMatchLimitAll : kSecMatchLimitOne,
    ]
    // Asking for the data of EVERY item is errSecParam (-50); only request the
    // secret when we're fetching a single named item.
    if !all { q[kSecReturnData as String] = true }
    if let s = service { q[kSecAttrService as String] = s }
    if let a = account { q[kSecAttrAccount as String] = a }
    return q
}

let args = CommandLine.arguments
guard args.count >= 2 else {
    FileHandle.standardError.write("usage: kcget get|has|list [args]\n".data(using: .utf8)!)
    exit(2)
}
let cmd = args[1]

switch cmd {
case "get", "has":
    guard args.count >= 3 else { exit(2) }
    let service = args[2]
    let account = args.count > 3 ? args[3] : nil
    var out: CFTypeRef?
    let st = SecItemCopyMatching(query(service: service, account: account, all: false) as CFDictionary, &out)
    if st == errSecSuccess, let d = out as? [String: Any] {
        // Prefer the synchronized copy if several match.
        if let data = d[kSecValueData as String] as? Data,
           let s = String(data: data, encoding: .utf8) {
            if cmd == "get" { print(s, terminator: "") } else { print("present") }
            exit(0)
        }
    }
    if cmd == "has" { print("missing"); exit(1) }
    FileHandle.standardError.write("not found (OSStatus \(st))\n".data(using: .utf8)!)
    exit(1)

case "list":
    let needle = args.count > 2 ? args[2].lowercased() : nil
    // Passwords.app saves website logins as INTERNET passwords (kSecClassInternetPassword),
    // which is a different class from generic passwords. Search both, or the item
    // looks missing when it is simply in the other class.
    let classes: [(String, CFString)] = [
        ("generic ", kSecClassGenericPassword),
        ("internet", kSecClassInternetPassword),
    ]
    var total = 0, shown = 0
    for (label, cls) in classes {
        var q: [String: Any] = [
            kSecClass as String: cls,
            kSecAttrSynchronizable as String: kSecAttrSynchronizableAny,
            kSecReturnAttributes as String: true,
            kSecMatchLimit as String: kSecMatchLimitAll,
        ]
        var out: CFTypeRef?
        let st = SecItemCopyMatching(q as CFDictionary, &out)
        guard st == errSecSuccess, let items = out as? [[String: Any]] else { continue }
        for it in items {
            total += 1
            let svc = (it[kSecAttrService as String] as? String)
                   ?? (it[kSecAttrServer as String] as? String) ?? ""
            let acct = (it[kSecAttrAccount as String] as? String) ?? ""
            let sync = (it[kSecAttrSynchronizable as String] as? Bool) ?? false
            if let nd = needle, !(svc.lowercased().contains(nd) || acct.lowercased().contains(nd)) { continue }
            print("\(label)  \(sync ? "icloud" : "local ")  \(svc)  [acct: \(acct)]")
            shown += 1
        }
    }
    FileHandle.standardError.write("\(shown) shown of \(total) total (generic + internet)\n".data(using: .utf8)!)
    exit(0)

default:
    exit(2)
}
