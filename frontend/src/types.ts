export interface RegisterRequest {
  name: string;
  email: string;
  marketing_consent?: boolean;
}

export interface SessionData {
  token?: string;
  ip_address: string;
  authenticated: boolean;
  expires_at?: string;
}

export interface RegisterResponse {
  success: boolean;
  message?: string;
  error?: string;
  session?: SessionData;
}

export interface StatusResponse {
  authenticated: boolean;
  ip_address: string;
  expires_at?: string;
}
