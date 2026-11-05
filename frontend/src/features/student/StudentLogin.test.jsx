import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import StudentLogin from './StudentLogin';
import apiFetch, { clearAuth } from '../../api';

vi.mock('../../api', () => ({ default: vi.fn(), clearAuth: vi.fn() }));
vi.mock('../../config', () => ({ BACKEND_URL: 'http://backend.test' }));
vi.mock('../../components/GoogleSignIn', () => ({ default: () => null }));
vi.mock('../../hooks/useCaptcha', () => ({
  useCaptcha: () => ({
    captchaToken: 'captcha-token',
    captchaImage: 'data:image/png;base64,test',
    captchaLoading: false,
    loadCaptcha: vi.fn(),
  }),
}));

function CurrentPath() {
  return <output data-testid="path">{useLocation().pathname}</output>;
}

beforeEach(() => {
  localStorage.clear();
  vi.mocked(apiFetch).mockReset();
  vi.mocked(clearAuth).mockReset();
});

describe('student login', () => {
  it('uses apiFetch for the public login and saves the authenticated identity', async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      ok: true,
      json: async () => ({ session_token: 'student-token', student_id: 'S123' }),
    });
    const { container } = render(
      <MemoryRouter initialEntries={['/student-login']}>
        <StudentLogin />
        <CurrentPath />
      </MemoryRouter>,
    );

    fireEvent.change(container.querySelector('#student_number'), { target: { value: 'S123' } });
    fireEvent.change(container.querySelector('#email'), { target: { value: 's123@ue.edu.ph' } });
    fireEvent.change(container.querySelector('#access_code'), { target: { value: 'access' } });
    fireEvent.change(container.querySelector('#antibot'), { target: { value: '1234' } });
    fireEvent.click(screen.getByRole('button', { name: 'Log In' }));

    await waitFor(() => expect(apiFetch).toHaveBeenCalledOnce());
    const [url, options] = vi.mocked(apiFetch).mock.calls[0];
    expect(url).toBe('http://backend.test/api/auth/login');
    expect(options.skipAuth).toBe(true);
    expect(options.skipUnauthorizedRedirect).toBe(true);
    expect(clearAuth).toHaveBeenCalledOnce();
    expect(localStorage.getItem('session_token')).toBe('student-token');
    expect(localStorage.getItem('student_id')).toBe('S123');
    await waitFor(() => expect(screen.getByTestId('path')).toHaveTextContent('/consent'));
  });
});
