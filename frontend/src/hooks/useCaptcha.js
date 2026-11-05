import { useCallback, useEffect, useState } from 'react';
import { BACKEND_URL } from '../config';

/** Shared server-issued CAPTCHA flow for both login portals. */
export function useCaptcha(setError) {
  const [captchaToken, setCaptchaToken] = useState('');
  const [captchaImage, setCaptchaImage] = useState('');
  const [captchaLoading, setCaptchaLoading] = useState(false);

  const loadCaptcha = useCallback(async ({ keepError = false } = {}) => {
    setCaptchaLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/captcha`, { cache: 'no-store' });
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();
      setCaptchaToken(data.token);
      setCaptchaImage(data.image);
    } catch {
      setCaptchaToken('');
      setCaptchaImage('');
      if (!keepError) setError('Could not load the verification image. Please press refresh.');
    } finally {
      setCaptchaLoading(false);
    }
  }, [setError]);

  useEffect(() => {
    loadCaptcha();
  }, [loadCaptcha]);

  return { captchaToken, captchaImage, captchaLoading, loadCaptcha };
}
