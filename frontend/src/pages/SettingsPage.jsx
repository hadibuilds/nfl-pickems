import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Cropper from 'react-easy-crop';
import toast from 'react-hot-toast';
import PageLayout from '../components/common/PageLayout';
import { useAuth } from '../context/AuthContext';
import Modal from '../components/common/Modal';

export default function SettingsPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const { userInfo, refreshUser } = useAuth();
  
  // User data state
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
  });
  
  // Password change state
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [changingPassword, setChangingPassword] = useState(false);
  
  // Avatar cropping state
  const [avatarSrc, setAvatarSrc] = useState(null);
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState(null);
  const [showCropper, setShowCropper] = useState(false);
  const [avatarUploading, setAvatarUploading] = useState(false);
  
  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  
  // Get CSRF token
  const getCookie = (name) => {
    const cookie = document.cookie.split('; ').find((row) => row.startsWith(name + '='));
    return cookie ? decodeURIComponent(cookie.split('=')[1]) : null;
  };
  
  // Use user data from AuthContext
  useEffect(() => {
    if (userInfo) {
      setUser(userInfo);
      setFormData({
        first_name: userInfo.first_name || '',
        last_name: userInfo.last_name || '',
        email: userInfo.email || '',
      });
      setLoading(false);
    } else {
      // If no user info, redirect to login
      navigate('/login');
    }
  }, [userInfo, navigate]);

  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };
  
  // Handle password form input changes
  const handlePasswordInputChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  // Handle profile form submission
  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setSaving(true);
    
    try {
      const response = await fetch(`${API_BASE}/accounts/api/profile/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        credentials: 'include',
        body: JSON.stringify(formData)
      });
      
      if (response.ok) {
        const updatedUser = await response.json();
        setUser(updatedUser);
        await refreshUser();
        toast.success('Profile updated successfully!');
      } else {
        const errorData = await response.json();
        toast.error(errorData.detail || 'Failed to update profile');
      }
    } catch (error) {
      console.error('Error updating profile:', error);
      toast.error('Failed to update profile');
    } finally {
      setSaving(false);
    }
  };
  
  // Handle password change form submission
  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (passwordData.new_password !== passwordData.confirm_password) {
      toast.error('New passwords do not match');
      return;
    }
    if (passwordData.new_password.length < 5) {
      toast.error('Password must be at least 5 characters long');
      return;
    }
    setChangingPassword(true);
    try {
      const response = await fetch(`${API_BASE}/accounts/api/change-password/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        credentials: 'include',
        body: JSON.stringify({
          current_password: passwordData.current_password,
          new_password: passwordData.new_password
        })
      });
      if (response.ok) {
        toast.success('Password changed successfully!');
        setPasswordData({
          current_password: '',
          new_password: '',
          confirm_password: ''
        });
      } else {
        const errorData = await response.json();
        toast.error(errorData.detail || 'Failed to change password');
      }
    } catch (error) {
      console.error('Error changing password:', error);
      toast.error('Failed to change password');
    } finally {
      setChangingPassword(false);
    }
  };
  
  // Handle avatar file selection
  const handleAvatarSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        toast.error('File size must be less than 5MB');
        return;
      }
      if (!file.type.startsWith('image/')) {
        toast.error('Please select an image file');
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        setAvatarSrc(reader.result);
        setShowCropper(true);
        setCrop({ x: 0, y: 0 });
        setZoom(1);
      };
      reader.readAsDataURL(file);
    }
  };
  
  // Handle crop complete
  const onCropComplete = (_, croppedArea) => {
    setCroppedAreaPixels(croppedArea);
  };
  
  // Create cropped image blob
  const createCroppedImage = async () => {
    try {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const image = new Image();
      return new Promise((resolve) => {
        image.onload = () => {
          const { width, height, x, y } = croppedAreaPixels;
          canvas.width = 400;
          canvas.height = 400;
          ctx.drawImage(
            image,
            x, y, width, height,
            0, 0, 400, 400
          );
          canvas.toBlob(resolve, 'image/jpeg', 0.9);
        };
        image.src = avatarSrc;
      });
    } catch (error) {
      console.error('Error creating cropped image:', error);
      return null;
    }
  };
  
  // Upload cropped avatar
  const handleAvatarUpload = async () => {
    setAvatarUploading(true);
    try {
      const croppedBlob = await createCroppedImage();
      if (!croppedBlob) {
        toast.error('Failed to process image');
        return;
      }
      const formData = new FormData();
      formData.append('avatar', croppedBlob, 'avatar.jpg');
      const response = await fetch(`${API_BASE}/accounts/api/avatar/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
        },
        credentials: 'include',
        body: formData
      });
      if (response.ok) {
        const result = await response.json();
        // Add cache busting timestamp to avatar URL
        const avatarWithCacheBust = result.avatar ? `${result.avatar}?t=${Date.now()}` : null;
        setUser(prev => ({ ...prev, avatar: avatarWithCacheBust }));
        setShowCropper(false);
        setAvatarSrc(null);
        const refreshResult = await refreshUser();
        if (refreshResult.success) {
          setTimeout(() => {
            toast.success('Avatar updated successfully! 📸');
          }, 200);
        } else {
          toast.success('Avatar updated successfully!');
        }
      } else {
        const errorData = await response.json();
        toast.error(errorData.detail || 'Failed to upload avatar');
      }
    } catch (error) {
      console.error('Error uploading avatar:', error);
      toast.error('Failed to upload avatar');
    } finally {
      setAvatarUploading(false);
    }
  };
  
  // Delete avatar
  const handleDeleteAvatar = async () => {
    if (!window.confirm('Are you sure you want to delete your avatar?')) return;
    try {
      const response = await fetch(`${API_BASE}/accounts/api/avatar/`, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
        },
        credentials: 'include'
      });
      if (response.ok) {
        setUser(prev => ({ ...prev, avatar: null }));
        await refreshUser();
        toast.success('Avatar deleted successfully!');
      } else {
        toast.error('Failed to delete avatar');
      }
    } catch (error) {
      console.error('Error deleting avatar:', error);
      toast.error('Failed to delete avatar');
    }
  };
  
  if (loading) {
    return (
      <PageLayout backgroundColor="#1E1E20" maxWidth="max-w-4xl">
        <div className="text-center text-white py-12">
          <div className="inline-flex items-center">
            <svg className="animate-spin h-8 w-8 text-violet-500 mr-3" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8"></path>
            </svg>
            Loading settings...
          </div>
        </div>
      </PageLayout>
    );
  }
  
  return (
    <PageLayout backgroundColor="#1E1E20" maxWidth="max-w-4xl">
      {/* Header */}
      <div className="mx-auto mb-8 text-center">
        <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold text-white mb-2 font-bebas tracking-wider">Settings</h1>
        <p className="mt-2 text-sm text-gray-400">
          Manage your profile and preferences
        </p>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
        {/* Avatar Section */}
        <div className="lg:col-span-1">
          <div className="homepage-glass-section p-6">
            <div className="homepage-glass-content">
              <h2 className="homepage-section-title">Avatar</h2>
              <div className="flex flex-col items-center">
                {/* Avatar Display */}
                <div className="relative mb-4">
                  <div 
                    className="w-32 h-32 rounded-full bg-gray-600 flex items-center justify-center text-4xl font-bold text-white overflow-hidden"
                    style={{
                      backgroundImage: user?.avatar ? `url(${user.avatar})` : 'none',
                      backgroundSize: 'cover',
                      backgroundPosition: 'center'
                    }}
                  >
                    {!user?.avatar && (
                      user?.first_name?.charAt(0) || user?.username?.charAt(0) || 'U'
                    )}
                  </div>
                </div>
                
                {/* Avatar Actions */}
                <div className="flex flex-col gap-2 w-full">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white rounded-lg transition-colors"
                  >
                    Upload New Avatar
                  </button>
                  
                  {user?.avatar && (
                    <button
                      onClick={handleDeleteAvatar}
                      className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                    >
                      Delete Avatar
                    </button>
                  )}
                </div>
                
                <p className="text-xs homepage-section-content mt-2 text-center" style={{ color: '#9ca3af' }}>
                  JPG, PNG, GIF or WebP. Max 5MB.
                </p>
              </div>
              
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleAvatarSelect}
                className="hidden"
              />
            </div>
          </div>
        </div>
        
        {/* Profile Form */}
        <div className="lg:col-span-2">
          <form onSubmit={handleSaveProfile} className="homepage-glass-section p-6">
            <div className="homepage-glass-content">
              <h2 className="homepage-section-title">Profile Information</h2>
              {/* 2x2 on >=sm, 1-col on phones */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                {/* First Name */}
                <div>
                  <label htmlFor="first_name" className="block text-sm font-medium text-gray-300 mb-2">
                    First Name
                  </label>
                  <input
                    type="text"
                    id="first_name"
                    name="first_name"
                    value={formData.first_name}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 bg-[#1f1f1f] border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                    required
                  />
                </div>

                {/* Last Name */}
                <div>
                  <label htmlFor="last_name" className="block text-sm font-medium text-gray-300 mb-2">
                    Last Name
                  </label>
                  <input
                    type="text"
                    id="last_name"
                    name="last_name"
                    value={formData.last_name}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 bg-[#1f1f1f] border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                  />
                </div>

                {/* Email */}
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                    Email Address
                  </label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    autoComplete="email"
                    className="w-full px-3 py-2 bg-[#1f1f1f] border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                    required
                  />
                </div>

                {/* Username (read-only) */}
                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-gray-300 mb-2">
                    Username
                  </label>
                  <input
                    type="text"
                    id="username"
                    value={user?.username || ''}
                    disabled
                    readOnly
                    autoComplete="username"
                    className="w-full px-3 py-2 rounded-lg text-white bg-gray-800 border border-gray-700 opacity-60 cursor-not-allowed"
                    aria-disabled="true"
                    tabIndex={-1}
                  />
                  <p className="mt-1 text-xs text-gray-400">This cannot be changed.</p>
                </div>
              </div>

              <div className="flex gap-4">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 px-6 py-3 bg-violet-600 hover:bg-violet-700 disabled:bg-violet-800 text-white rounded-lg font-medium transition-colors"
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
                
                <button
                  type="button"
                  onClick={() => navigate('/')}
                  className="px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </form>
        </div>
        
        {/* Password Change Section */}
        <div className="lg:col-span-3 mt-8">
          <form onSubmit={handleChangePassword} className="homepage-glass-section p-6">
            <div className="homepage-glass-content">
              <h2 className="homepage-section-title">Change Password</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label htmlFor="current_password" className="block text-sm font-medium text-gray-300 mb-2">
                    Current Password
                  </label>
                  <input
                    type="password"
                    id="current_password"
                    name="current_password"
                    value={passwordData.current_password}
                    onChange={handlePasswordInputChange}
                    className="w-full px-3 py-2 bg-[#1f1f1f] border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                    required
                  />
                </div>
                
                <div>
                  <label htmlFor="new_password" className="block text-sm font-medium text-gray-300 mb-2">
                    New Password
                  </label>
                  <input
                    type="password"
                    id="new_password"
                    name="new_password"
                    value={passwordData.new_password}
                    onChange={handlePasswordInputChange}
                    autoComplete="new-password"
                    className="w-full px-3 py-2 bg-[#1f1f1f] border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                    required
                  />
                </div>
                
                <div>
                  <label htmlFor="confirm_password" className="block text-sm font-medium text-gray-300 mb-2">
                    Confirm New Password
                  </label>
                  <input
                    type="password"
                    id="confirm_password"
                    name="confirm_password"
                    value={passwordData.confirm_password}
                    onChange={handlePasswordInputChange}
                    autoComplete="new-password"
                    className="w-full px-3 py-2 bg-[#1f1f1f] border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                    required
                  />
                </div>
              </div>
              
              <div className="mt-6 flex gap-4 justify-center">
                <button
                  type="submit"
                  disabled={changingPassword}
                  className="px-6 py-3 bg-red-600 hover:bg-red-700 disabled:bg-red-800 text-white rounded-lg font-medium transition-colors"
                >
                  {changingPassword ? 'Changing Password...' : 'Change Password'}
                </button>
                
                <button
                  type="button"
                  onClick={() => setPasswordData({ current_password: '', new_password: '', confirm_password: '' })}
                  className="px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-colors"
                >
                  Clear
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      {/* Avatar Cropper Modal (Portal + scroll lock handled inside Modal component) */}
      <Modal
        isOpen={showCropper}
        onClose={() => {
          setShowCropper(false);
          setAvatarSrc(null);
        }}
        ariaLabel="Crop your avatar"
      >
        <h3 className="homepage-section-title">Crop Your Avatar</h3>

        <div className="relative w-full h-48 sm:h-64 mb-4 bg-black rounded-lg overflow-hidden">
          <Cropper
            image={avatarSrc}
            crop={crop}
            zoom={zoom}
            aspect={1}
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onCropComplete={onCropComplete}
            cropShape="round"
            showGrid={false}
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Zoom
          </label>
          <input
            type="range"
            min={1}
            max={3}
            step={0.1}
            value={zoom}
            onChange={(e) => setZoom(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleAvatarUpload}
            disabled={avatarUploading}
            className="flex-1 px-4 py-2 bg-violet-600 hover:bg-violet-700 disabled:bg-violet-800 text-white rounded-lg transition-colors"
          >
            {avatarUploading ? 'Uploading...' : 'Save Avatar'}
          </button>
          <button
            onClick={() => {
              setShowCropper(false);
              setAvatarSrc(null);
            }}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
          >
            Cancel
          </button>
        </div>
      </Modal>
    </PageLayout>
  );
}
