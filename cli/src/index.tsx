#!/usr/bin/env -S npx tsx
import React from 'react';
import { render } from 'ink';
import App from './App.js';

if (!process.stdin.isTTY) {
  // Ink needs a real terminal (raw mode) for interactive input.
  console.error('octopus needs an interactive terminal (TTY). Run it directly in your terminal.');
  process.exit(1);
}

render(<App version="0.1.0" />);
