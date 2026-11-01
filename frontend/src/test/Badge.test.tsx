import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Badge, PriorityBadge } from '../components/common/Badge';

describe('Badge Components', () => {
  it('renders standard Badge with different variants', () => {
    const { rerender } = render(<Badge variant="critical">Stockout</Badge>);
    expect(screen.getByText('Stockout')).toBeInTheDocument();

    rerender(<Badge variant="success">Mitigated</Badge>);
    expect(screen.getByText('Mitigated')).toBeInTheDocument();
  });

  it('renders PriorityBadge correctly for critical, high, medium, low', () => {
    const { rerender } = render(<PriorityBadge priority="Critical" />);
    expect(screen.getByText('Critical')).toBeInTheDocument();

    rerender(<PriorityBadge priority="High" />);
    expect(screen.getByText('High')).toBeInTheDocument();

    rerender(<PriorityBadge priority="Medium" />);
    expect(screen.getByText('Medium')).toBeInTheDocument();

    rerender(<PriorityBadge priority="Low" />);
    expect(screen.getByText('Low')).toBeInTheDocument();
  });
});

