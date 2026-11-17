import Vision; import CoreImage; import AppKit
let a = CommandLine.arguments; let url = URL(fileURLWithPath: a[1])
let ci = CIImage(contentsOf: url)!
let h = VNImageRequestHandler(ciImage: ci)
let r = VNGenerateForegroundInstanceMaskRequest()
try h.perform([r])
guard let o = r.results?.first else { print("no subject"); exit(1) }
let buf = try o.generateMaskedImage(ofInstances: o.allInstances, from: h, croppedToInstancesExtent: false)
let out = CIImage(cvPixelBuffer: buf)
let ctx = CIContext()
try ctx.writePNGRepresentation(of: out, to: URL(fileURLWithPath: a[2]), format: .RGBA8, colorSpace: CGColorSpaceCreateDeviceRGB())
print("ok", o.allInstances.count)
