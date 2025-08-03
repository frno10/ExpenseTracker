# Deployment Guide

## Requirements Files Overview

We have multiple requirements files for different deployment scenarios:

### Core Requirements Files

1. **`requirements-render.txt`** ⭐ **RECOMMENDED FOR DEPLOYMENT**
   - Ultra-stable versions tested to work on Render.com
   - Minimal dependencies to avoid conflicts
   - Use this for production deployments

2. **`requirements-minimal.txt`** 
   - Absolute minimum packages needed
   - Fallback if render requirements fail

3. **`requirements-prod.txt`**
   - Production requirements with more features
   - May have dependency conflicts on some platforms

4. **`requirements.txt`**
   - Full development requirements
   - Not recommended for production deployment

### Optional Feature Requirements

5. **`requirements-observability.txt`**
   - OpenTelemetry monitoring and tracing
   - Install separately: `pip install -r requirements-observability.txt`

6. **`requirements-parsing.txt`**
   - File parsing capabilities (PDF, Excel, images)
   - Install separately: `pip install -r requirements-parsing.txt`

## Deployment Instructions

### For Render.com (Recommended)

1. **Use the render.yaml configuration** (already set up)
2. **Or manually set build command:**
   ```bash
   cd backend && pip install --upgrade pip && pip install -r requirements-render.txt
   ```

### For Other Platforms

1. **Try render requirements first:**
   ```bash
   pip install -r requirements-render.txt
   ```

2. **If that fails, try minimal:**
   ```bash
   pip install -r requirements-minimal.txt
   ```

3. **Add optional features as needed:**
   ```bash
   pip install -r requirements-observability.txt  # For monitoring
   pip install -r requirements-parsing.txt        # For file processing
   ```

## Troubleshooting

### Common Issues

1. **Dependency Conflicts**
   - Use `requirements-render.txt` - it has tested compatible versions
   - Avoid mixing different requirements files

2. **Missing System Dependencies**
   - `python-magic` requires `libmagic1` on Linux
   - `Pillow` may need image libraries
   - These are in optional requirements files

3. **Build Timeouts**
   - Use `requirements-render.txt` for faster builds
   - It has fewer packages and pre-built wheels

### Platform-Specific Notes

- **Render.com**: Use `requirements-render.txt`
- **Heroku**: Use `requirements-render.txt` or `requirements-minimal.txt`
- **Docker**: Install system dependencies in Dockerfile
- **Local Development**: Use `requirements.txt`

## Version Strategy

The `requirements-render.txt` uses older, stable versions that are guaranteed to:
- Have pre-built wheels available
- Work together without conflicts
- Deploy quickly on cloud platforms
- Provide all core functionality needed

If you need newer features, install them separately after the core deployment works.