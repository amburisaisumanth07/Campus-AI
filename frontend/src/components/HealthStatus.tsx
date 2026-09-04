import React, { useEffect, useState } from 'react';
import { checkHealth } from '../services/api';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';

export const HealthStatus: React.FC = () => {
  const [status, setStatus] = useState<'Checking...' | 'Connected' | 'Unavailable'>('Checking...');

  useEffect(() => {
    let isMounted = true;
    
    const verifyHealth = async () => {
      try {
        await checkHealth();
        if (isMounted) setStatus('Connected');
      } catch (error) {
        if (isMounted) setStatus('Unavailable');
      }
    };

    verifyHealth();

    // Check periodically
    const interval = setInterval(verifyHealth, 10000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="health-status">
      {status === 'Checking...' && (
        <span className="status checking">
          <Loader2 className="icon spin" size={16} /> Checking...
        </span>
      )}
      {status === 'Connected' && (
        <span className="status connected">
          <CheckCircle className="icon" size={16} /> Connected
        </span>
      )}
      {status === 'Unavailable' && (
        <span className="status unavailable">
          <XCircle className="icon" size={16} /> Unavailable
        </span>
      )}
    </div>
  );
};
