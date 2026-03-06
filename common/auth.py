"""Authentication and authorization services for Genesis X.

Provides:
- JWTManager for secure token generation and validation
- PasswordHasher using bcrypt for secure password hashing
- AuthService for complete authentication flow (login, register, refresh)
- Permission checking decorators for RBAC
- Token blacklist management for logout
- Password reset token generation and validation
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple, Callable
from functools import wraps
import secrets
import uuid
import hashlib

import bcrypt
import jwt
from sqlalchemy.orm import Session

from ..models.user import User, UserSession, UserPreferences, UserRole, UserStatus


class PasswordHasher:
    """Secure password hashing using bcrypt.

    Features:
    - Configurable work factor (default: 12 rounds)
    - Automatic salt generation
    - Secure password verification
    - Timing-attack resistant comparison
    """

    def __init__(self, rounds: int = 12):
        """Initialize password hasher.

        Args:
            rounds: bcrypt work factor (4-31, higher is slower but more secure)
        """
        if rounds < 4 or rounds > 31:
            raise ValueError("bcrypt rounds must be between 4 and 31")
        self.rounds = rounds

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: Plain text password to hash

        Returns:
            Base64-encoded bcrypt hash string
        """
        if not password:
            raise ValueError("Password cannot be empty")

        # Convert to bytes and hash
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password_bytes, salt)

        # Return as string (bcrypt returns bytes)
        return hashed.decode('utf-8')

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against a hash.

        Args:
            password: Plain text password to verify
            password_hash: Previously hashed password

        Returns:
            True if password matches hash, False otherwise
        """
        if not password or not password_hash:
            return False

        try:
            password_bytes = password.encode('utf-8')
            hash_bytes = password_hash.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception:
            # Any error in verification should return False
            return False

    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """Validate password meets security requirements.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if len(password) > 128:
            return False, "Password must be at most 128 characters long"

        # Check for at least one uppercase, one lowercase, one digit
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        if not (has_upper and has_lower and has_digit):
            return False, "Password must contain uppercase, lowercase, and digit characters"

        return True, ""


class JWTManager:
    """JWT token generation and validation manager.

    Features:
    - Access and refresh token generation
    - Token validation and expiry checking
    - Custom claims support
    - Blacklist integration for logout
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expires: int = 15,  # minutes
        refresh_token_expires: int = 7,  # days
    ):
        """Initialize JWT manager.

        Args:
            secret_key: Secret key for signing tokens (keep secure!)
            algorithm: JWT signing algorithm (default: HS256)
            access_token_expires: Access token lifetime in minutes
            refresh_token_expires: Refresh token lifetime in days
        """
        if not secret_key or len(secret_key) < 32:
            raise ValueError("Secret key must be at least 32 characters")

        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expires = timedelta(minutes=access_token_expires)
        self.refresh_token_expires = timedelta(days=refresh_token_expires)

    def generate_access_token(
        self,
        user_id: int,
        username: str,
        role: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, datetime]:
        """Generate an access token.

        Args:
            user_id: User ID
            username: Username
            role: User role
            additional_claims: Optional additional JWT claims

        Returns:
            Tuple of (token, jti, expires_at)
        """
        now = datetime.now(timezone.utc)
        expires_at = now + self.access_token_expires
        jti = str(uuid.uuid4())

        payload = {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "type": "access",
            "jti": jti,
            "iat": now,
            "exp": expires_at,
        }

        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, jti, expires_at

    def generate_refresh_token(
        self,
        user_id: int,
        username: str,
    ) -> Tuple[str, str, datetime]:
        """Generate a refresh token.

        Args:
            user_id: User ID
            username: Username

        Returns:
            Tuple of (token, jti, expires_at)
        """
        now = datetime.now(timezone.utc)
        expires_at = now + self.refresh_token_expires
        jti = str(uuid.uuid4())

        payload = {
            "sub": str(user_id),
            "username": username,
            "type": "refresh",
            "jti": jti,
            "iat": now,
            "exp": expires_at,
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, jti, expires_at

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            jwt.ExpiredSignatureError: Token has expired
            jwt.InvalidTokenError: Token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise jwt.ExpiredSignatureError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")

    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify token and check type.

        Args:
            token: JWT token string
            token_type: Expected token type ("access" or "refresh")

        Returns:
            Decoded payload if valid, None otherwise
        """
        try:
            payload = self.decode_token(token)
            if payload.get("type") != token_type:
                return None
            return payload
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None


class AuthService:
    """Complete authentication service.

    Provides:
    - User registration with validation
    - Login with credentials
    - Token refresh
    - Logout with token blacklist
    - Password reset
    """

    def __init__(
        self,
        db_session: Session,
        jwt_secret: str,
        password_hasher: Optional[PasswordHasher] = None,
        jwt_manager: Optional[JWTManager] = None,
    ):
        """Initialize authentication service.

        Args:
            db_session: SQLAlchemy database session
            jwt_secret: Secret key for JWT signing
            password_hasher: Password hasher instance (creates default if None)
            jwt_manager: JWT manager instance (creates default if None)
        """
        self.db = db_session
        self.password_hasher = password_hasher or PasswordHasher()
        self.jwt_manager = jwt_manager or JWTManager(secret_key=jwt_secret)

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: str = UserRole.USER.value,
    ) -> Tuple[bool, Optional[User], str]:
        """Register a new user.

        Args:
            username: Unique username
            email: Unique email address
            password: Plain text password
            full_name: Optional full name
            role: User role (default: USER)

        Returns:
            Tuple of (success, user, error_message)
        """
        # Validate password strength
        is_valid, error_msg = self.password_hasher.validate_password_strength(password)
        if not is_valid:
            return False, None, error_msg

        # Check if username exists
        existing_user = self.db.query(User).filter(User.username == username).first()
        if existing_user:
            return False, None, "Username already exists"

        # Check if email exists
        existing_email = self.db.query(User).filter(User.email == email.lower()).first()
        if existing_email:
            return False, None, "Email already exists"

        # Hash password
        password_hash = self.password_hasher.hash_password(password)

        # Generate unique tenant ID
        tenant_id = f"tenant_{uuid.uuid4().hex[:16]}"

        # Create user
        try:
            user = User(
                username=username,
                email=email.lower(),
                password_hash=password_hash,
                full_name=full_name,
                role=role,
                status=UserStatus.ACTIVE.value,
                tenant_id=tenant_id,
            )

            self.db.add(user)
            self.db.flush()  # Get user ID without committing

            # Create default preferences
            preferences = UserPreferences(user_id=user.id)
            self.db.add(preferences)

            self.db.commit()
            self.db.refresh(user)

            return True, user, ""

        except Exception as e:
            self.db.rollback()
            return False, None, f"Registration failed: {str(e)}"

    def login(
        self,
        username_or_email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Authenticate user and generate tokens.

        Args:
            username_or_email: Username or email address
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client user agent string

        Returns:
            Tuple of (success, token_data, error_message)
            token_data contains: access_token, refresh_token, user_info
        """
        # Find user by username or email
        user = self.db.query(User).filter(
            (User.username == username_or_email) | (User.email == username_or_email.lower())
        ).first()

        if not user:
            return False, None, "Invalid credentials"

        # Check if user can login
        if not user.can_login():
            if user.is_locked:
                return False, None, f"Account locked until {user.account_locked_until}"
            elif user.status == UserStatus.SUSPENDED.value:
                return False, None, "Account suspended"
            else:
                return False, None, "Account not active"

        # Verify password
        if not self.password_hasher.verify_password(password, user.password_hash):
            user.record_failed_login()
            self.db.commit()
            return False, None, "Invalid credentials"

        # Reset failed login attempts on success
        user.reset_failed_logins()
        user.last_login_at = datetime.now(timezone.utc)
        user.last_activity_at = datetime.now(timezone.utc)

        # Generate tokens
        access_token, access_jti, access_expires = self.jwt_manager.generate_access_token(
            user.id, user.username, user.role
        )
        refresh_token, refresh_jti, refresh_expires = self.jwt_manager.generate_refresh_token(
            user.id, user.username
        )

        # Create session records
        access_session = UserSession(
            user_id=user.id,
            jti=access_jti,
            token_type="access",
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=access_expires,
        )

        refresh_session = UserSession(
            user_id=user.id,
            jti=refresh_jti,
            refresh_token_jti=refresh_jti,
            token_type="refresh",
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=refresh_expires,
        )

        self.db.add(access_session)
        self.db.add(refresh_session)
        self.db.commit()

        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": int(self.jwt_manager.access_token_expires.total_seconds()),
            "user": user.to_dict(),
        }

        return True, token_data, ""

    def refresh_access_token(
        self, refresh_token: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Tuple of (success, token_data, error_message)
        """
        # Verify refresh token
        payload = self.jwt_manager.verify_token(refresh_token, token_type="refresh")
        if not payload:
            return False, None, "Invalid or expired refresh token"

        jti = payload.get("jti")
        user_id = int(payload.get("sub"))

        # Check if session exists and is valid
        session = self.db.query(UserSession).filter(
            UserSession.jti == jti,
            UserSession.user_id == user_id,
        ).first()

        if not session or not session.is_valid:
            return False, None, "Session invalid or revoked"

        # Get user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.can_login():
            return False, None, "User cannot login"

        # Generate new access token
        access_token, access_jti, access_expires = self.jwt_manager.generate_access_token(
            user.id, user.username, user.role
        )

        # Create new access session
        access_session = UserSession(
            user_id=user.id,
            jti=access_jti,
            token_type="access",
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            expires_at=access_expires,
        )

        self.db.add(access_session)
        self.db.commit()

        token_data = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": int(self.jwt_manager.access_token_expires.total_seconds()),
        }

        return True, token_data, ""

    def logout(self, token: str) -> Tuple[bool, str]:
        """Logout user by revoking token.

        Args:
            token: Access or refresh token to revoke

        Returns:
            Tuple of (success, message)
        """
        try:
            payload = self.jwt_manager.decode_token(token)
            jti = payload.get("jti")

            # Revoke session
            session = self.db.query(UserSession).filter(UserSession.jti == jti).first()
            if session:
                session.revoke()

                # If it's a refresh token, revoke all associated access tokens
                if session.token_type == "refresh":
                    access_sessions = self.db.query(UserSession).filter(
                        UserSession.refresh_token_jti == jti,
                        UserSession.token_type == "access",
                    ).all()
                    for access_session in access_sessions:
                        access_session.revoke()

                self.db.commit()
                return True, "Logged out successfully"

            return False, "Session not found"

        except Exception as e:
            return False, f"Logout failed: {str(e)}"

    def is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is in blacklist (revoked).

        Args:
            jti: JWT ID to check

        Returns:
            True if token is blacklisted, False otherwise
        """
        session = self.db.query(UserSession).filter(UserSession.jti == jti).first()
        if not session:
            return True  # Unknown token is considered blacklisted

        return session.is_revoked or not session.is_valid

    def generate_password_reset_token(self, email: str) -> Tuple[bool, Optional[str], str]:
        """Generate password reset token for user.

        Args:
            email: User email address

        Returns:
            Tuple of (success, reset_token, message)
        """
        user = self.db.query(User).filter(User.email == email.lower()).first()
        if not user:
            # Don't reveal if email exists
            return True, None, "If email exists, reset instructions have been sent"

        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)
        reset_token_hash = hashlib.sha256(reset_token.encode()).hexdigest()

        # Store hash and expiry (15 minutes)
        user.password_reset_token = reset_token_hash
        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(minutes=15)

        self.db.commit()

        return True, reset_token, "Reset token generated"

    def reset_password_with_token(
        self, reset_token: str, new_password: str
    ) -> Tuple[bool, str]:
        """Reset password using reset token.

        Args:
            reset_token: Password reset token
            new_password: New password

        Returns:
            Tuple of (success, message)
        """
        # Hash the token to compare with stored hash
        reset_token_hash = hashlib.sha256(reset_token.encode()).hexdigest()

        # Find user with matching token
        user = self.db.query(User).filter(
            User.password_reset_token == reset_token_hash
        ).first()

        if not user:
            return False, "Invalid reset token"

        # Check if token has expired
        if user.password_reset_expires < datetime.now(timezone.utc):
            return False, "Reset token has expired"

        # Validate new password
        is_valid, error_msg = self.password_hasher.validate_password_strength(new_password)
        if not is_valid:
            return False, error_msg

        # Update password
        user.password_hash = self.password_hasher.hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None

        # Revoke all existing sessions for security
        for session in user.sessions:
            session.revoke()

        self.db.commit()

        return True, "Password reset successfully"


# Decorator functions for permission checking

def require_auth(func: Callable) -> Callable:
    """Decorator to require authentication for a function.

    Usage:
        @require_auth
        def protected_function(current_user: User, ...):
            ...

    修复：添加实际的认证检查逻辑
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract current_user from kwargs (framework-specific)
        current_user = kwargs.get('current_user')
        if not current_user:
            raise PermissionError("Authentication required")

        # 验证用户是否有效（检查必要字段）
        if not hasattr(current_user, 'id') or not hasattr(current_user, 'username'):
            raise PermissionError("Invalid user object")

        # 检查用户是否被禁用
        if hasattr(current_user, 'is_active') and not current_user.is_active:
            raise PermissionError("User account is disabled")

        return func(*args, **kwargs)
    return wrapper


def require_role(required_role: str) -> Callable:
    """Decorator to require specific role for a function.

    Args:
        required_role: Required user role (admin, user, guest)

    Usage:
        @require_role("admin")
        def admin_only_function(current_user: User, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract current_user from kwargs (framework-specific)
            current_user = kwargs.get('current_user')
            if not current_user or current_user.role != required_role:
                raise PermissionError(f"Requires {required_role} role")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_role(*roles: str) -> Callable:
    """Decorator to require any of the specified roles.

    Args:
        roles: List of acceptable roles

    Usage:
        @require_any_role("admin", "user")
        def function_for_users_and_admins(current_user: User, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user or current_user.role not in roles:
                raise PermissionError(f"Requires one of: {', '.join(roles)}")
            return func(*args, **kwargs)
        return wrapper
    return decorator
