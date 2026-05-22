from importlib.metadata import distributions
packages = [dist.metadata['Name'] for dist in distributions()]
openbb_pkgs = [p for p in packages if p.lower().startswith('openbb')]
# Filter out meta-packages or duplicates if needed, but collect-all is usually safe
# openbb-cli is already target, but including it doesn't hurt
# Convert package names to module names (replace hyphen with underscore)
# But 'openbb' stays 'openbb'
# 'openbb-core' -> 'openbb_core'
module_names = [p.replace('-', '_') for p in openbb_pkgs]

cmd = " ".join([f"--collect-all {m} --copy-metadata {p}" for m, p in zip(module_names, openbb_pkgs)])
print(cmd)
