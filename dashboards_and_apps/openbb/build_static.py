from openbb_core.app.static.package_builder import PackageBuilder
print("Building static package...")
pb = PackageBuilder(lint=False)
pb.build()
print("Build complete.")
