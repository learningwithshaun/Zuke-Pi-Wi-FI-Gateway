import { RegisterRequest, RegisterResponse, StatusResponse } from '../types';

const API_BASE = '/api/captive-portal';

export async function registerCustomer(data: RegisterRequest): Promise<RegisterResponse> {
  try {
    const res = await fetch(`${API_BASE}/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    const body = await res.json().catch(() => null);

    if (!res.ok) {
      return {
        success: false,
        error: body?.error || `Registration failed (HTTP ${res.status}). Please try again.`,
      };
    }

    if (body?.session?.token) {
      try {
        localStorage.setItem('zuke_session_token', body.session.token);
      } catch {
        // ignore localStorage errors (e.g. private browsing mode)
      }
    }

    return body as RegisterResponse;
  } catch (err) {
    return {
      success: false,
      error: 'Unable to reach the network gateway. Please ensure you are connected to Zuke WiFi.',
    };
  }
}

export async function checkStatus(): Promise<StatusResponse | null> {
  try {
    let token: string | null = null;
    try {
      token = localStorage.getItem('zuke_session_token');
    } catch {
      // ignore
    }

    const url = token ? `${API_BASE}/status?token=${encodeURIComponent(token)}` : `${API_BASE}/status`;
    const res = await fetch(url, { method: 'GET' });

    if (!res.ok) {
      return null;
    }

    const data: StatusResponse = await res.json();
    return data;
  } catch {
    return null;
  }
}
