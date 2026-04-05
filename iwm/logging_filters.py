class IgnoreDevserverTLSNoise:
    SUPPRESSED_PATTERNS = (
        "You're accessing the development server over HTTPS, but it only supports HTTP.",
        "Bad request version",
        "Bad request syntax",
    )

    def filter(self, record):
        message = record.getMessage()
        return not any(pattern in message for pattern in self.SUPPRESSED_PATTERNS)
