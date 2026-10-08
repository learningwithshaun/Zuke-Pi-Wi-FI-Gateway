import React, { useState } from 'react';
import { User, Mail, ShieldCheck } from 'lucide-react';
import { registerCustomer } from '../services/api';
import { RegisterResponse } from '../types';
import { LoadingSpinner } from './LoadingSpinner';
import { ErrorAlert } from './ErrorAlert';

interface RegistrationFormProps {
  onSuccess: (data: RegisterResponse) => void;
}

const EMAIL_REGEX = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;

export const RegistrationForm: React.FC<RegistrationFormProps> = ({ onSuccess }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [marketingConsent, setMarketingConsent] = useState(false);

  const [nameError, setNameError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validate = (): boolean => {
    let isValid = true;
    const trimmedName = name.trim();
    if (!trimmedName) {
      setNameError('Please enter your name.');
      isValid = false;
    } else {
      setNameError(null);
    }

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setEmailError('Please enter your email address.');
      isValid = false;
    } else if (!EMAIL_REGEX.test(trimmedEmail)) {
      setEmailError('Please enter a valid email address.');
      isValid = false;
    } else {
      setEmailError(null);
    }
    return isValid;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      const response = await registerCustomer({
        name: name.trim(),
        email: email.trim(),
        marketing_consent: marketingConsent,
      });

      if (response.success) {
        onSuccess(response);
      } else {
        setApiError(response.error || 'Registration failed. Please check your details.');
      }
    } catch {
      setApiError('Unable to connect to gateway. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {apiError && <ErrorAlert message={apiError} onDismiss={() => setApiError(null)} />}

      <div>
        <label htmlFor="customer-name" className="block text-xs font-semibold text-zuke-dark mb-1">
          Name <span className="text-zuke-orange">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <User className="w-4 h-4" />
          </div>
          <input
            id="customer-name"
            type="text"
            value={name}
            onChange={(e) => { setName(e.target.value); if (nameError) setNameError(null); }}
            disabled={isSubmitting}
            placeholder="e.g. Amanda"
            className={`w-full pl-9 pr-3 py-2.5 bg-white border text-sm rounded-xl outline-none transition-all ${
              nameError ? 'border-red-400 focus:ring-2 focus:ring-red-200' : 'border-slate-300 focus:border-zuke-orange focus:ring-2 focus:ring-orange-100'
            } disabled:bg-slate-100`}
          />
        </div>
        {nameError && <p className="text-xs text-red-500 font-medium mt-1">{nameError}</p>}
      </div>

      <div>
        <label htmlFor="customer-email" className="block text-xs font-semibold text-zuke-dark mb-1">
          Email <span className="text-zuke-orange">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <Mail className="w-4 h-4" />
          </div>
          <input
            id="customer-email"
            type="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value); if (emailError) setEmailError(null); }}
            disabled={isSubmitting}
            placeholder="e.g. customer@example.com"
            className={`w-full pl-9 pr-3 py-2.5 bg-white border text-sm rounded-xl outline-none transition-all ${
              emailError ? 'border-red-400 focus:ring-2 focus:ring-red-200' : 'border-slate-300 focus:border-zuke-orange focus:ring-2 focus:ring-orange-100'
            } disabled:bg-slate-100`}
          />
        </div>
        {emailError && <p className="text-xs text-red-500 font-medium mt-1">{emailError}</p>}
      </div>

      <div className="pt-1">
        <label className="flex items-start gap-2.5 cursor-pointer text-xs text-zuke-gray leading-snug">
          <input
            type="checkbox"
            checked={marketingConsent}
            onChange={(e) => setMarketingConsent(e.target.checked)}
            disabled={isSubmitting}
            className="mt-0.5 rounded text-zuke-orange focus:ring-zuke-orange border-slate-300 h-4 w-4"
          />
          <span>I agree to receive Zuke marketing communications.</span>
        </label>
      </div>

      <div className="pt-2">
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-zuke-orange hover:bg-zuke-orange-hover text-white text-sm font-semibold rounded-xl shadow-md hover:shadow-lg transition-all active:scale-[0.99] disabled:opacity-70 disabled:cursor-not-allowed"
        >
          {isSubmitting ? <LoadingSpinner size="sm" label="Connecting..." /> : <span>Get Internet Access</span>}
        </button>
      </div>

      <div className="text-center pt-1">
        <p className="text-[11px] text-slate-400 flex items-center justify-center gap-1">
          <ShieldCheck className="w-3.5 h-3.5 text-zuke-teal" />
          <span>Your information is safely processed for Wi-Fi access.</span>
        </p>
      </div>
    </form>
  );
};
