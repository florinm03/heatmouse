# heatmouse
Mouse Analytics Heatmap Tool

### Setup

### Step 1: Create Project Directory
```bash
mkdir mouse-analytics
cd mouse-analytics
```

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv mouse_env
mouse_env\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv mouse_env
source mouse_env/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install pynput matplotlib numpy scipy seaborn
```

### Step 4: Save the Script
- Copy the Python script to a file named `mouse_analytics.py`
- Place it in your `mouse-analytics` folder

### Step 5: Run the Tool
```bash
python main.py
```

---

## System-Specific Requirements

### Windows
- No additional setup required
- Windows Defender might ask for permissions

### macOS
- **Important**: You'll need to grant accessibility permissions
- Go to: System Preferences → Security & Privacy → Privacy → Accessibility
- Add Terminal (or your Python IDE) to the list of allowed applications
- You might also need to add Python itself

### Linux
- Install tkinter if not already available:
  ```bash
  sudo apt install python3-tk
  ```
- For some distributions, you might need:
  ```bash
  sudo apt install python3-dev
  ```

---

## Troubleshooting

### Permission Issues (macOS)
If you get permission errors:
1. Open System Preferences
2. Go to Security & Privacy → Privacy
3. Click on "Accessibility" or "Input Monitoring"
4. Click the lock to make changes
5. Add your terminal application or Python
