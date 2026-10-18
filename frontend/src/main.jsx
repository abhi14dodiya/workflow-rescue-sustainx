import React from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource-variable/manrope';
import App from './App.jsx';
import './style.css';
import './theme.css';
import './journey.css';
import './usability.css';

createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>);
