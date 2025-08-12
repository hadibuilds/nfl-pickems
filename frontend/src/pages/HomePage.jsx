import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Typewriter, { TypewriterClass } from 'typewriter-effect';

function HomePage() {
  const { userInfo, logout } = useAuth();
  const weeks = [1, 2, 3, 4];

  if (!weeks || weeks.length === 0) {
    return <p>No weeks available</p>;
  }

  return (
    <div>
      <h1>
      <Typewriter
        onInit={(typewriter) => {
          typewriter.changeDelay(75)
          typewriter.typeString("Good luck to everyone,")
            .changeDelay(75)
            .pauseFor(1500)
            .deleteAll()
            .start();
          typewriter.typeString("except Abdallah.")
            .changeDelay(75)
            .pauseFor(1500)
            .deleteAll()
            .start();
          typewriter.typeString("Happy Pickems!")
        }}
      />
      </h1>
      {userInfo ? (
        <div>
          <h2 className="text-white text-2xl mt-10">Good luck, {userInfo.username}!</h2>
          <Link
            to="/weeks"
            className="mt-10 inline-flex items-center space-x-2 px-5 py-2 rounded-full bg-violet-100 text-violet-700 font-semibold text-lg hover:bg-violet-200 hover:text-violet-600 transition"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-7 w-7 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            <span>Games</span>
          </Link>
        </div>
      ) : (
        <>
          <h2>you are not logged in</h2>
          <p className="text-center text-small">
            <Link to="/login" style={{ color: '#007BFF', fontSize: '16px' }}>
              Login
            </Link>
          </p>
          <p className="text-center text-small">
            <Link to="/signup" style={{ color: '#007BFF', fontSize: '16px' }}>
              Sign Up
            </Link>
          </p>
        </>
      )}
    </div>
  );
}

export default HomePage;