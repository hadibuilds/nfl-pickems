import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Typewriter, { TypewriterClass } from 'typewriter-effect';
import confetti from 'canvas-confetti';

function HomePage() {
  const { userInfo, logout } = useAuth();
  const navigate = useNavigate();
  const weeks = [1, 2, 3, 4];

  const handleConfetti = () => {
    // Trigger confetti animation
    confetti({
      particleCount: 100,
      spread: 70,
      origin: { y: 0.6 }
    });
    
    // Navigate immediately
    navigate('/weeks');
  };

  if (!weeks || weeks.length === 0) {
    return <p>No weeks available</p>;
  }

  return (
    <div>
      <h1>
      <Typewriter
        onInit={(typewriter) => {
          typewriter.changeDelay(75)
          typewriter.typeString("Good luck everyone,\n")
            .changeDelay(75)
            .pauseFor(1500)
            .start();
          typewriter.typeString("<span style='font-size: 0.7em; opacity: 0.8;'>except Abdallah.</span>")
            .changeDelay(75)
            .pauseFor(1000)
            .deleteChars(18)
            .start();
          typewriter.typeString("!")
        }}
      />
      </h1>
      {userInfo ? (
        <div>
          <h2 className="text-white text-2xl mt-10">Welcome back, {userInfo.username}!</h2>
          <button
            onClick={handleConfetti}
            className="mt-10 inline-flex items-center space-x-2 px-5 py-2 rounded-full font-semibold text-lg text-white hover:text-violet-400 transition hover:-translate-y-1 cursor-pointer"
            style={{ backgroundColor: '#2d2d2d' }}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-7 w-7 text-violet-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M9 5l7 7-7 7" />
            </svg>
            <span>Enter</span>
          </button>
        </div>
      ) : (
        <>
          <h2>you are not logged in</h2>
          <p className="text-center text-small">
            <Link to="/login" style={{ color: '#8B5CF6', fontSize: '16px' }}>
              Login
            </Link>
          </p>
          <p className="text-center text-small">
            <Link to="/signup" style={{ color: '#8B5CF6', fontSize: '16px' }}>
              Sign Up
            </Link>
          </p>
        </>
      )}
    </div>
  );
}

export default HomePage;