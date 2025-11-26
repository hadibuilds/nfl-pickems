/*
 * Error Boundary Component
 * Catches JavaScript errors anywhere in the child component tree
 * Displays a fallback UI instead of crashing the entire app
 * Logs errors for debugging in development
 */

import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log the error details
    console.error('🚨 Error Boundary Caught Error:', error);
    console.error('📍 Error Info:', errorInfo);
    
    // Store error details in state for display in development
    this.setState({
      error: error,
      errorInfo: errorInfo
    });

    // In production, you might want to send this to an error reporting service
    // Example: logErrorToService(error, errorInfo);
  }

  handleRetry = () => {
    // Reset error state to try rendering again
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI based on the boundary level
      const { level = 'component', customMessage } = this.props;

      if (level === 'game') {
        // Compact error for individual game cards
        return (
          <div className="game-box" style={{ 
            backgroundColor: '#101118', 
            borderRadius: '16px',
            padding: '20px',
            margin: '20px 0',
            textAlign: 'center',
            border: '2px solid #EF4444'
          }}>
            <div style={{ color: '#EF4444', fontSize: '2rem', marginBottom: '8px' }}>⚠️</div>
            <h3 style={{ color: 'white', fontSize: '1rem', marginBottom: '8px' }}>
              Game Card Error
            </h3>
            <p style={{ color: '#9ca3af', fontSize: '0.875rem', marginBottom: '12px' }}>
              This game encountered an error and couldn't load properly.
            </p>
            <button
              onClick={this.handleRetry}
              className="team-button"
              style={{ 
                backgroundColor: '#EF4444',
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.875rem'
              }}
            >
              Try Again
            </button>
          </div>
        );
      }

      if (level === 'page') {
        // Larger error for page-level issues
        return (
          <div style={{ 
            minHeight: '50vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '2rem',
            backgroundColor: '#05060A',
            color: 'white'
          }}>
            <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>💥</div>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem', textAlign: 'center' }}>
              {customMessage || 'Page Error'}
            </h2>
            <p style={{ color: '#9ca3af', marginBottom: '1.5rem', textAlign: 'center', maxWidth: '500px' }}>
              Something went wrong loading this page. This might be a temporary issue.
            </p>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={this.handleRetry}
                style={{ 
                  backgroundColor: '#8B5CF6',
                  color: 'white',
                  border: 'none',
                  padding: '12px 24px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '1rem'
                }}
              >
                Try Again
              </button>
              <button
                onClick={() => window.location.href = '/weeks'}
                style={{ 
                  backgroundColor: '#101118',
                  color: 'white',
                  border: '1px solid #4B5563',
                  padding: '12px 24px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '1rem'
                }}
              >
                Go to Games
              </button>
            </div>
            
            {/* Show error details in development */}
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details style={{ 
                marginTop: '2rem', 
                padding: '1rem', 
                backgroundColor: '#101118', 
                borderRadius: '8px',
                maxWidth: '80vw',
                overflow: 'auto'
              }}>
                <summary style={{ cursor: 'pointer', marginBottom: '1rem' }}>
                  🐛 Error Details (Development Only)
                </summary>
                <pre style={{ 
                  fontSize: '0.75rem', 
                  color: '#EF4444',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}>
                  {this.state.error.toString()}
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}
          </div>
        );
      }

      // Default component-level error
      return (
        <div style={{ 
          padding: '1rem',
          margin: '1rem 0',
          backgroundColor: '#2d2d2d',
          border: '1px solid #EF4444',
          borderRadius: '8px',
          textAlign: 'center'
        }}>
          <div style={{ color: '#EF4444', fontSize: '1.5rem', marginBottom: '0.5rem' }}>⚠️</div>
          <p style={{ color: 'white', marginBottom: '0.5rem' }}>
            {customMessage || 'Something went wrong with this component.'}
          </p>
          <button
            onClick={this.handleRetry}
            style={{ 
              backgroundColor: '#EF4444',
              color: 'white',
              border: 'none',
              padding: '6px 12px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.875rem'
            }}
          >
            Retry
          </button>
        </div>
      );
    }

    // If no error, render children normally
    return this.props.children;
  }
}

export default ErrorBoundary;