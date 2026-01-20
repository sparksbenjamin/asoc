"""
ASoc TLS Auto-Configuration

Provides simple TLS setup with sensible defaults.
Users just pass tls=True and certificates are handled automatically.

Usage:
    # Enable TLS (auto-generates self-signed cert if none exists)
    node = NodeReady(..., tls=True)
    
    # Or provide your own certificates
    node = NodeReady(..., tls=True, cert_file='cert.pem', key_file='key.pem')
"""

import ssl
import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import tempfile


class TLSConfig:
    """
    Manages TLS configuration with smart defaults
    
    Hierarchy:
    1. User-provided cert_file/key_file
    2. Default location (~/.asoc/certs/)
    3. Auto-generate temporary self-signed cert
    """
    
    def __init__(self):
        self.default_cert_dir = Path.home() / ".asoc" / "certs"
        self.default_cert_file = self.default_cert_dir / "cert.pem"
        self.default_key_file = self.default_cert_dir / "key.pem"
    
    def get_or_create_certificates(
        self,
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Get certificate paths, creating them if needed
        
        Args:
            cert_file: Optional path to certificate
            key_file: Optional path to private key
            
        Returns:
            (cert_path, key_path)
        """
        # Option 1: User provided both
        if cert_file and key_file:
            if not Path(cert_file).exists():
                raise FileNotFoundError(f"Certificate not found: {cert_file}")
            if not Path(key_file).exists():
                raise FileNotFoundError(f"Key not found: {key_file}")
            print(f"🔒 Using provided certificates:")
            print(f"   Cert: {cert_file}")
            print(f"   Key: {key_file}")
            return cert_file, key_file
        
        # Option 2: Check default location
        if self.default_cert_file.exists() and self.default_key_file.exists():
            print(f"🔒 Using existing certificates from {self.default_cert_dir}")
            return str(self.default_cert_file), str(self.default_key_file)
        
        # Option 3: Generate new self-signed certificate
        print(f"🔒 No certificates found. Generating self-signed certificate...")
        return self._generate_self_signed()
    
    def _generate_self_signed(self) -> Tuple[str, str]:
        """Generate self-signed certificate in default location"""
        
        # Create directory
        self.default_cert_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Try using OpenSSL (best option)
            cmd = [
                "openssl", "req", "-x509", "-newkey", "rsa:2048",
                "-keyout", str(self.default_key_file),
                "-out", str(self.default_cert_file),
                "-days", "365",
                "-nodes",
                "-subj", "/CN=asoc-node"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"✓ Generated self-signed certificate")
                print(f"   Location: {self.default_cert_dir}")
                print(f"   Valid for: 365 days")
                
                # Set secure permissions
                self.default_key_file.chmod(0o600)
                
                return str(self.default_cert_file), str(self.default_key_file)
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Fallback: Use Python's cryptography library if available
        try:
            return self._generate_with_cryptography()
        except ImportError:
            pass
        
        # Last resort: Create temporary cert (less secure, but works)
        print("⚠️  OpenSSL not found. Using temporary certificate.")
        print("   For production, install OpenSSL or provide your own certificates.")
        return self._generate_temporary()
    
    def _generate_with_cryptography(self) -> Tuple[str, str]:
        """Generate certificate using Python's cryptography library"""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, u"asoc-node"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).sign(private_key, hashes.SHA256())
        
        # Write certificate
        with open(self.default_cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        # Write private key
        with open(self.default_key_file, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        self.default_key_file.chmod(0o600)
        
        print(f"✓ Generated certificate using Python cryptography")
        return str(self.default_cert_file), str(self.default_key_file)
    
    def _generate_temporary(self) -> Tuple[str, str]:
        """Generate temporary certificate (fallback)"""
        # This is a last resort - creates minimal cert
        # Not recommended for production!
        
        tmpdir = Path(tempfile.gettempdir()) / "asoc_temp_certs"
        tmpdir.mkdir(exist_ok=True)
        
        cert_file = tmpdir / "temp_cert.pem"
        key_file = tmpdir / "temp_key.pem"
        
        # Create minimal self-signed cert using Python
        import ssl as ssl_module
        
        # This is a placeholder - in reality you'd need cryptography
        # For now, raise error suggesting installation
        raise RuntimeError(
            "Cannot generate TLS certificates automatically.\n"
            "Please either:\n"
            "  1. Install OpenSSL: apt-get install openssl\n"
            "  2. Install cryptography: pip install cryptography\n"
            "  3. Provide your own certificates: tls=True, cert_file='...', key_file='...'\n"
        )
    
    def create_ssl_context(
        self,
        cert_file: str,
        key_file: str,
        is_server: bool = True,
        verify_mode: str = "none"
    ) -> ssl.SSLContext:
        """
        Create SSL context with sensible defaults
        
        Args:
            cert_file: Path to certificate
            key_file: Path to private key
            is_server: True for server, False for client
            verify_mode: 'none', 'optional', or 'required'
            
        Returns:
            Configured SSLContext
        """
        if is_server:
            purpose = ssl.Purpose.CLIENT_AUTH
        else:
            purpose = ssl.Purpose.SERVER_AUTH
        
        context = ssl.create_default_context(purpose)
        context.load_cert_chain(cert_file, key_file)
        
        # Set verification mode
        if verify_mode == "none":
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        elif verify_mode == "optional":
            context.check_hostname = False
            context.verify_mode = ssl.CERT_OPTIONAL
        elif verify_mode == "required":
            context.verify_mode = ssl.CERT_REQUIRED
        else:
            raise ValueError(f"Invalid verify_mode: {verify_mode}")
        
        # Use modern TLS only
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        return context


def setup_tls(
    tls: bool = False,
    cert_file: Optional[str] = None,
    key_file: Optional[str] = None,
    ca_file: Optional[str] = None,
    verify_peer: bool = False,
    is_server: bool = True
) -> Optional[ssl.SSLContext]:
    """
    Setup TLS with smart defaults
    
    Args:
        tls: Whether to enable TLS
        cert_file: Optional certificate file path
        key_file: Optional key file path
        ca_file: Optional CA file for peer verification
        verify_peer: Whether to verify peer certificates
        is_server: Whether this is a server or client
        
    Returns:
        SSLContext if TLS enabled, None otherwise
        
    Examples:
        # Simple: auto-generate certificates
        ssl_ctx = setup_tls(tls=True)
        
        # With your own certificates
        ssl_ctx = setup_tls(tls=True, cert_file='my.crt', key_file='my.key')
        
        # With peer verification
        ssl_ctx = setup_tls(tls=True, ca_file='ca.crt', verify_peer=True)
    """
    if not tls:
        return None
    
    config = TLSConfig()
    
    # Get or create certificates
    cert_path, key_path = config.get_or_create_certificates(cert_file, key_file)
    
    # Determine verification mode
    if verify_peer:
        if not ca_file:
            raise ValueError("ca_file required when verify_peer=True")
        verify_mode = "required"
    else:
        verify_mode = "none"
    
    # Create SSL context
    ssl_context = config.create_ssl_context(
        cert_path,
        key_path,
        is_server=is_server,
        verify_mode=verify_mode
    )
    
    # Load CA if provided
    if ca_file:
        ssl_context.load_verify_locations(ca_file)
    
    return ssl_context


# Convenience function for certificates
def generate_certificates(output_dir: Optional[str] = None):
    """
    Generate self-signed certificates manually
    
    Args:
        output_dir: Where to save certificates (default: ~/.asoc/certs/)
    """
    config = TLSConfig()
    
    if output_dir:
        config.default_cert_dir = Path(output_dir)
        config.default_cert_file = config.default_cert_dir / "cert.pem"
        config.default_key_file = config.default_cert_dir / "key.pem"
    
    cert, key = config._generate_self_signed()
    
    print(f"\n✓ Certificates generated!")
    print(f"   Certificate: {cert}")
    print(f"   Private key: {key}")
    print(f"\nTo use with ASoc:")
    print(f"   node = NodeReady(..., tls=True)")
    print(f"   # or")
    print(f"   node = NodeReady(..., tls=True, cert_file='{cert}', key_file='{key}')")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "generate":
        # Generate certificates
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        generate_certificates(output_dir)
    else:
        print("ASoc TLS Configuration Tool")
        print()
        print("Usage:")
        print("  python tls_config.py generate [output_dir]")
        print()
        print("Examples:")
        print("  python tls_config.py generate                    # Generate in ~/.asoc/certs/")
        print("  python tls_config.py generate ./my-certs/        # Generate in custom location")
