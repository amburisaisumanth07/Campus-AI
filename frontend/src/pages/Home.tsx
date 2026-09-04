import React from 'react';
import { ArrowRight, Sparkles, Book, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const Home: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="home-container">
      <header className="hero-section">
        <div className="hero-badge">
          <Sparkles size={16} />
          <span>Next-Generation Learning</span>
        </div>
        <h1 className="hero-title">
          Welcome to <span className="highlight">CampusAI</span>
        </h1>
        <p className="hero-subtitle">
          AI-Powered College Knowledge & Student Support System
        </p>
        <button className="primary-button" onClick={() => navigate('/dashboard')}>
          Get Started <ArrowRight size={18} />
        </button>
      </header>

      <section className="features-section">
        <div className="feature-card">
          <div className="feature-icon-wrapper">
            <Book size={24} />
          </div>
          <h3>Intelligent Knowledge</h3>
          <p>Access your university's entire knowledge base instantly through advanced semantic search.</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon-wrapper">
            <Users size={24} />
          </div>
          <h3>Student Support</h3>
          <p>Get personalized guidance, course recommendations, and administrative help 24/7.</p>
        </div>
      </section>
    </div>
  );
};
