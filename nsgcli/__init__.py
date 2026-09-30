import warnings

# Suppress urllib3 NotOpenSSLWarning (e.g. on macOS with LibreSSL) and other urllib3 warnings
warnings.filterwarnings('ignore', category=Warning, module='.*urllib3.*')
