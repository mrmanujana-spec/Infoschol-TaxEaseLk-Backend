from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from supabase_client import supabase


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# -------------------------
# Request Models
# -------------------------

class RegisterRequest(BaseModel):
    email: str
    password: str
    confirm_password: str
    role: str
    license_number: str | None = None

class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


# -------------------------
# Sign Up
# -------------------------

@router.post("/register")
def register(user_data: RegisterRequest):

    if user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )

    if user_data.role not in ["auditor", "business"]:
        raise HTTPException(
            status_code=400,
            detail="Role must be auditor or business"
        )

    if user_data.role == "auditor" and not user_data.license_number:
        raise HTTPException(
            status_code=400,
            detail="License number is required for auditor"
        )
    try:
        response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
   		 "data": {
       			 "role": user_data.role,
       			 "license_number": 
	user_data.license_number
	}
    }
        })

        if response.user is None:
            raise HTTPException(
                status_code=400,
                detail="Sign up failed"
            )

        return {
            "message": "User registered successfully",
            "email": response.user.email,
            "user_id": response.user.id,
            "role": user_data.role
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# -------------------------
# Sign In
# -------------------------

@router.post("/login")
def login(user_data: LoginRequest):

    try:
        response = supabase.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password
        })

        if response.user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        return {
            "message": "Login successful",
            "email": response.user.email,
            "user_id": response.user.id,
            "session": response.session.access_token
        }

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )


# -------------------------
# Forgot Password
# -------------------------

@router.post("/forgot-password")
def forgot_password(user_data: ForgotPasswordRequest):

    try:
        supabase.auth.reset_password_for_email(
            user_data.email
        )

        return {
            "message": "Password reset email sent",
            "email": user_data.email
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )