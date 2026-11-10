import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import CounselorBottomNav from './CounselorBottomNav';

function renderNav(props = {}) {
  return render(
    <CounselorBottomNav
      activePage="overview"
      setActivePage={() => {}}
      {...props}
    />,
  );
}

describe('counselor mobile navigation sheet', () => {
  it('traps keyboard focus, closes on Escape, and restores focus to More', async () => {
    const user = userEvent.setup();
    renderNav();

    const trigger = screen.getByRole('button', { name: 'More navigation options' });
    await user.click(trigger);

    const dialog = screen.getByRole('dialog', { name: 'Additional Counselor Navigation' });
    const close = screen.getByRole('button', { name: 'Close menu' });
    await waitFor(() => expect(close).toHaveFocus());

    await user.tab({ shift: true });
    expect(screen.getByRole('button', { name: /Resolved Cases/ })).toHaveFocus();
    await user.tab();
    expect(close).toHaveFocus();

    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(dialog).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
  });

  it('closes the More sheet when the counselor drawer opens', async () => {
    const user = userEvent.setup();
    const { rerender } = renderNav();
    await user.click(screen.getByRole('button', { name: 'More navigation options' }));
    expect(screen.getByRole('dialog', { name: 'Additional Counselor Navigation' })).toBeInTheDocument();

    rerender(
      <CounselorBottomNav key="drawer-open" activePage="overview" setActivePage={() => {}} drawerOpen />,
    );
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Additional Counselor Navigation' })).not.toBeInTheDocument());
    rerender(
      <CounselorBottomNav key="drawer-closed" activePage="overview" setActivePage={() => {}} drawerOpen={false} />,
    );
    expect(screen.queryByRole('dialog', { name: 'Additional Counselor Navigation' })).not.toBeInTheDocument();
  });
});
