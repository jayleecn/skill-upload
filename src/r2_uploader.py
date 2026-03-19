"""Cloudflare R2 Uploader - AWS Signature V4 implementation using standard library."""
import hashlib
import hmac
import datetime
import urllib.request
from typing import Optional
from pathlib import Path


class R2Uploader:
    """Upload files to Cloudflare R2 using AWS Signature V4 (no external deps)."""

    def __init__(
        self,
        access_key_id: str,
        secret_access_key: str,
        endpoint: str,
        bucket: str,
        public_url: Optional[str] = None
    ):
        """
        Initialize R2 uploader.

        Args:
            access_key_id: R2 Access Key ID
            secret_access_key: R2 Secret Access Key
            endpoint: R2 endpoint (e.g., https://xxx.r2.cloudflarestorage.com)
            bucket: Bucket name
            public_url: Public URL prefix for accessing uploaded files
        """
        self.access_key = access_key_id
        self.secret_key = secret_access_key
        self.endpoint = endpoint.rstrip('/')
        self.bucket = bucket
        self.public_url = public_url.rstrip('/') if public_url else None

        # Extract host from endpoint
        self.host = self.endpoint.replace('https://', '').replace('http://', '')

    def _get_signature_key(self, date_stamp: str, region: str, service: str) -> bytes:
        """Generate AWS Signature V4 signing key."""
        k_date = hmac.new(f"AWS4{self.secret_key}".encode(), date_stamp.encode(), hashlib.sha256).digest()
        k_region = hmac.new(k_date, region.encode(), hashlib.sha256).digest()
        k_service = hmac.new(k_region, service.encode(), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, "aws4_request".encode(), hashlib.sha256).digest()
        return k_signing

    def upload(self, file_path: str, key: str) -> dict:
        """
        Upload a file to R2.

        Args:
            file_path: Path to local file
            key: Object key in bucket (e.g., "skills/mp-editor.zip")

        Returns:
            dict with status, url, size, etc.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read file
        with open(path, 'rb') as f:
            body = f.read()

        body_hash = hashlib.sha256(body).hexdigest()

        # Generate timestamp
        t = datetime.datetime.now(datetime.timezone.utc)
        date_stamp = t.strftime('%Y%m%d')
        amz_date = t.strftime('%Y%m%dT%H%M%SZ')
        region = "auto"
        service = "s3"

        # Create canonical request
        canonical_uri = f"/{self.bucket}/{key}"
        canonical_headers = f"host:{self.host}\nx-amz-content-sha256:{body_hash}\nx-amz-date:{amz_date}\n"
        signed_headers = "host;x-amz-content-sha256;x-amz-date"

        canonical_request = f"PUT\n{canonical_uri}\n\n{canonical_headers}\n{signed_headers}\n{body_hash}"

        # Create string to sign
        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_hash = hashlib.sha256(canonical_request.encode()).hexdigest()
        string_to_sign = f"AWS4-HMAC-SHA256\n{amz_date}\n{credential_scope}\n{string_hash}"

        # Calculate signature
        signing_key = self._get_signature_key(date_stamp, region, service)
        signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

        # Authorization header
        auth_header = (
            f"AWS4-HMAC-SHA256 "
            f"Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        # Make request
        url = f"{self.endpoint}{canonical_uri}"
        headers = {
            "Authorization": auth_header,
            "x-amz-date": amz_date,
            "x-amz-content-sha256": body_hash,
            "Host": self.host,
            "Content-Length": str(len(body))
        }

        req = urllib.request.Request(url, data=body, headers=headers, method='PUT')

        try:
            with urllib.request.urlopen(req) as response:
                result = {
                    "success": True,
                    "status": response.status,
                    "key": key,
                    "size": len(body),
                    "bucket": self.bucket,
                }

                # Add public URL if configured
                if self.public_url:
                    result["url"] = f"{self.public_url}/{key}"

                return result

        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            return {
                "success": False,
                "status": e.code,
                "error": e.reason,
                "details": error_body[:500] if error_body else None
            }
