# JobTruth Browser Extension

Check job offers for scams directly from Gmail, LinkedIn, and WhatsApp Web.

## Installation

### Chrome/Edge (Developer Mode)

1. Open `chrome://extensions/` or `edge://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select the `extension` folder from this project
5. The JobTruth icon will appear in your toolbar

### Firefox

1. Open `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on"
3. Select `manifest.json` from the `extension` folder
4. The JobTruth icon will appear in your toolbar

## Usage

1. **Select text** in Gmail, LinkedIn, or WhatsApp Web containing a job offer
2. **Click the JobTruth icon** in your toolbar
3. **View the analysis** - trust score, warning signs, and risk level
4. **Click "Open JobTruth"** to see full details and save the analysis

## Features

- Analyze job offers without leaving Gmail/LinkedIn/WhatsApp
- Quick trust score and risk assessment
- See warning signs at a glance
- Open full JobTruth app for detailed analysis
- Save analyses to your account

## Permissions

- **activeTab**: To analyze the current page
- **scripting**: To extract text from emails and messages
- **storage**: To remember your preferences
- **Gmail, LinkedIn, WhatsApp Web**: To work on these platforms

## Privacy

- Text is only sent to JobTruth API for analysis
- No data is stored by the extension
- All analysis is done server-side
- Your selections are never logged or tracked
