import Foundation

let reconciler = "/usr/local/libexec/asimov-fixed"
let arguments = Array(CommandLine.arguments.dropFirst())

let process = Process()
process.executableURL = URL(fileURLWithPath: reconciler)
process.arguments = arguments
process.standardInput = FileHandle.standardInput
process.standardOutput = FileHandle.standardOutput
process.standardError = FileHandle.standardError

do {
    try process.run()
    process.waitUntilExit()
    exit(process.terminationStatus)
} catch {
    FileHandle.standardError.write(
        Data("asimov-launcher: \(error)\n".utf8)
    )
    exit(1)
}
