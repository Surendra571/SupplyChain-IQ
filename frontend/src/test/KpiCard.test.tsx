import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { KpiCard } from '../components/common/KpiCard';

describe('KpiCard Component', () => {
  it('renders title, value, and subtitle correctly', () => {
    render(
      <KpiCard
        title="Active Shortages"
        value={1405}
        subtitle="12-week horizon"
        variant="critical"
      />
    );

    expect(screen.getByText('Active Shortages')).toBeInTheDocument();
    expect(screen.getByText('1405')).toBeInTheDocument();
    expect(screen.getByText('12-week horizon')).toBeInTheDocument();
  });

  it('renders financial formatted values', () => {
    render(
      <KpiCard
        title="Revenue at Risk"
        value="$4,250,000"
        subtitle="Unmet critical demand"
        variant="warning"
      />
    );

    expect(screen.getByText('Revenue at Risk')).toBeInTheDocument();
    expect(screen.getByText('$4,250,000')).toBeInTheDocument();
  });
});

