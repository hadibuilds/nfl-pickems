import React from "react";
import { Link } from "react-router-dom";

export default function WeekSelector() {
  const totalWeeks = 18;
  const weeks = Array.from({ length: totalWeeks }, (_, i) => i + 1);

  return (
    <div className="min-h-screen bg-white dark:bg-[#1E1E20] text-gray-900 dark:text-white py-12 px-6">
      <h1 className="text-3xl text-center mb-10">Select a Week</h1>
      <div className="grid grid-cols-3 sm:grid-cols-6 lg:grid-cols-9 gap-4 justify-center">
        {weeks.map((week) => (
          <Link
            key={week}
            to={`/week/${week}`}
            className="inline-flex items-center space-x-2 px-5 py-2 rounded-full bg-[#2d2d2d] dark:bg-[#2d2d2d] text-white font-semibold text-base hover:bg-violet-100 hover:text-violet-600 transition"
          >
            <span>Week {week}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
