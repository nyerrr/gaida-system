import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router-dom';
import InformedConsent from './InformedConsent';
import { apiFetch } from '../../api';

vi.mock('../../api', () => ({
  apiFetch: vi.fn(),
  clearAuth: vi.fn(),
}));

function CurrentPath() {
  return <output data-testid="current-path">{useLocation().pathname}</output>;
}

function renderConsent() {
  return render(
    <MemoryRouter initialEntries={['/consent']}>
      <InformedConsent />
      <CurrentPath />
    </MemoryRouter>,
  );
}

function scrollTermsToEnd() {
  const terms = screen.getByRole('region', { name: 'Consent terms' });
  Object.defineProperties(terms, {
    clientHeight: { configurable: true, value: 300 },
    scrollHeight: { configurable: true, value: 500 },
  });
  terms.scrollTop = 200;
  fireEvent.scroll(terms);
}

beforeEach(() => {
  localStorage.clear();
  vi.mocked(apiFetch).mockReset();
});
afterEach(() => vi.unstubAllGlobals());

describe('informed consent', () => {
  it('exposes consent terms as a keyboard-focusable region', () => {
    renderConsent();
    expect(screen.getByRole('region', { name: 'Consent terms' })).toHaveAttribute('tabindex', '0');
  });

  it('keeps the checkbox locked until the terms reach the end', () => {
    renderConsent();
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toHaveAttribute('aria-disabled', 'true');
    expect(screen.getByText('Scroll to the end of the terms to enable this box.')).toBeInTheDocument();
    fireEvent.click(checkbox);
    expect(checkbox).not.toBeChecked();

    scrollTermsToEnd();
    expect(checkbox).toHaveAttribute('aria-disabled', 'false');
    expect(screen.queryByText('Scroll to the end of the terms to enable this box.')).not.toBeInTheDocument();
    expect(screen.queryByText('Scroll to continue')).not.toBeInTheDocument();
  });

  it('keeps the checkbox and both action buttons in keyboard order', async () => {
    const user = userEvent.setup();
    renderConsent();
    const terms = screen.getByRole('region', { name: 'Consent terms' });
    const checkbox = screen.getByRole('checkbox');
    const accept = screen.getByRole('button', { name: 'I Accept - Start Session' });
    const decline = screen.getByRole('button', { name: 'Decline & Logout' });

    scrollTermsToEnd();
    await user.click(checkbox);
    terms.focus();
    await user.tab();
    expect(checkbox).toHaveFocus();
    await user.tab();
    expect(accept).toHaveFocus();
    await user.tab();
    expect(decline).toHaveFocus();
  });

  it('submits consent using a UUID fallback and navigates on success', async () => {
    vi.stubGlobal('crypto', {
      getRandomValues: (bytes) => { bytes.fill(1); return bytes; },
    });
    vi.mocked(apiFetch).mockResolvedValue({ ok: true });
    renderConsent();

    scrollTermsToEnd();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'I Accept - Start Session' }));

    await waitFor(() => expect(apiFetch).toHaveBeenCalledOnce());
    const request = vi.mocked(apiFetch).mock.calls[0];
    const payload = JSON.parse(request[1].body);
    expect(payload.session_id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
    expect(localStorage.getItem('consent_given')).toBe('true');
    await waitFor(() => expect(screen.getByTestId('current-path')).toHaveTextContent('/student-dashboard'));
  });

  it('shows an in-page error when consent cannot be saved', async () => {
    vi.mocked(apiFetch).mockResolvedValue({ ok: false });
    renderConsent();

    scrollTermsToEnd();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'I Accept - Start Session' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('We could not save your consent');
    expect(localStorage.getItem('consent_given')).toBeNull();
  });
});
