import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [requiredExperienceMonths, setRequiredExperienceMonths] = useState('');
  const [skills, setSkills] = useState([{ name: '', weight: 0 }]);
  const [projects, setProjects] = useState(['']);
  const [numShortlist, setNumShortlist] = useState('');
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState([]);
  const [totalWeight, setTotalWeight] = useState(0);
  const [loading, setLoading] = useState(false);
  const [analyzingMessage, setAnalyzingMessage] = useState('');

  useEffect(() => {
    const total = skills.reduce((acc, skill) => acc + skill.weight, 0);
    setTotalWeight(total);
  }, [skills]);

  const handleAddSkill = () => {
    setSkills([...skills, { name: '', weight: 0 }]);
  };

  const handleSkillChange = (index, field, value) => {
    const newSkills = skills.slice();
    newSkills[index][field] = value;
    setSkills(newSkills);
  };

  const handleAddProject = () => {
    setProjects([...projects, '']);
  };

  const handleProjectChange = (index, value) => {
    const newProjects = projects.slice();
    newProjects[index] = value;
    setProjects(newProjects);
  };

  const handleFileChange = (event) => {
    setFiles(event.target.files);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setAnalyzingMessage('Analyzing resumes...');

    const formData = new FormData();
    formData.append('required_experience_months', requiredExperienceMonths);
    skills.forEach((skill) => {
        formData.append('required_skills[]', skill.name);
        formData.append('skill_weights[]', skill.weight);
    });
    projects.forEach((project) => {
        formData.append('required_projects[]', project);
    });
    formData.append('num_shortlist', numShortlist);
    Array.from(files).forEach((file) => {
        formData.append('files', file);
    });

    try {
        const response = await axios.post('http://127.0.0.1:5000/upload', formData);
        setResults(response.data);
        setAnalyzingMessage('Analysis complete!');
    } catch (error) {
        console.error('Detailed error:', error);
        if (error.response) {
            // Server responded with a status code other than 2xx
            setAnalyzingMessage(`Error: ${error.response.data.message || 'Server error'}`);
        } else if (error.request) {
            // Request was made but no response was received
            setAnalyzingMessage('Error: No response from server.');
        } else {
            // Something happened in setting up the request
            setAnalyzingMessage('Error: Request setup issue.');
        }
    } finally {
        setLoading(false);
    }
};


  return (
    <div className="App">
      <header>
        <div className="header-content">
          <h1 className="app-title">Spotter Bot</h1>
          <div className="auth-links">
            <a href="/login">Login</a>
            <a href="/signup">Sign Up</a>
          </div>
        </div>
      </header>
      <main>
        <div className="file-upload-section">
          <input
            type="file"
            multiple
            onChange={handleFileChange}
            id="file-upload"
            className="file-input"
          />
          <label htmlFor="file-upload" className="file-upload-label">
            <span className="plus-icon">+</span> Upload Resumes
          </label>
          <div className="file-count">
            {files.length > 0 && <p>{files.length} resume(s) uploaded</p>}
          </div>
        </div>
        {files.length > 0 && (
          <section className="upload-section">
            <h2>Easily shortlist resumes in seconds</h2>
            <form onSubmit={handleSubmit}>
              <div>
                <label>Required Months of Experience:</label>
                <input
                  type="number"
                  value={requiredExperienceMonths}
                  onChange={(e) => setRequiredExperienceMonths(e.target.value)}
                  required
                />
              </div>
              <div>
                <label>Skills (with weights):</label>
                {skills.map((skill, index) => (
                  <div className="skill-input" key={index}>
                    <input
                      type="text"
                      placeholder="Skill"
                      value={skill.name}
                      onChange={(e) => handleSkillChange(index, 'name', e.target.value)}
                      required
                    />
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={skill.weight}
                      onChange={(e) => {
                        const newWeight = parseInt(e.target.value);
                        const weightDifference = newWeight - skills[index].weight;
                        if (totalWeight + weightDifference <= 100) {
                          handleSkillChange(index, 'weight', newWeight);
                        }
                      }}
                      required
                    />
                    <span>{skill.weight}%</span>
                    <button type="button" onClick={() => handleAddSkill()}>+</button>
                  </div>
                ))}
                <div>Total Weight: {totalWeight}%</div>
              </div>
              <div>
                <label>Projects:</label>
                {projects.map((project, index) => (
                  <div className="project-input" key={index}>
                    <input
                      type="text"
                      placeholder="Project"
                      value={project}
                      onChange={(e) => handleProjectChange(index, e.target.value)}
                      required
                    />
                    <button type="button" onClick={() => handleAddProject()}>+</button>
                  </div>
                ))}
              </div>
              <div>
                <label>Number of Resumes to Shortlist:</label>
                <input
                  type="number"
                  value={numShortlist}
                  onChange={(e) => setNumShortlist(e.target.value)}
                  required
                />
              </div>
              <button type="submit" disabled={totalWeight !== 100 || loading}>
                {loading ? 'Analyzing...' : 'Analyze Resumes'}
              </button>
            </form>
            <p className="analyzing-message">{analyzingMessage}</p>
          </section>
        )}
        {files.length > 0 && !loading && (
          <section className="instructions">
            <h2>How to Use</h2>
            <ol>
              <li>Enter the required months of experience.</li>
              <li>Add the skills with their respective weights (total must be 100%).</li>
              <li>Specify the required projects.</li>
              <li>Enter the number of resumes to shortlist.</li>
              <li>Click the "Analyze Resumes" button to get the shortlisted results.</li>
            </ol>
          </section>
        )}
        {!loading && results.length > 0 && (
          <section className="results">
            <h2>Shortlisted Resumes</h2>
            <ul>
              {results.map((result, index) => (
                <li key={index}>
                  {result.name}: {result.score}
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
