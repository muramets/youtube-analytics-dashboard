# YouTube Analytics Dashboard

A Streamlit application for analyzing YouTube video performance data by time periods.

## Features

- **YouTube API Integration**: Fetches real-time view counts and publication dates
- **CSV Data Processing**: Handles YouTube Analytics export files
- **Time-based Categorization**: Organizes videos into 4 time periods:
  - Last 2 weeks
  - 2-4 weeks ago  
  - 1-3 months ago
  - More than 3 months ago
- **Rich Data Display**: Shows thumbnails, clickable video titles, and key metrics
- **Responsive Design**: Clean, modern interface optimized for data analysis

## Setup Instructions

### 1. Get YouTube API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable YouTube Data API v3
4. Create credentials (API Key)
5. Copy the API key for use in the application

### 2. Prepare Your Data

Export your YouTube Analytics data as CSV with these columns:
- Traffic source (containing YT_RELATED.{video_id} format)
- Source type
- Source title  
- Impressions
- Impressions click-through rate (%)
- Views
- Average view duration
- Watch time (hours)

**Note**: The application automatically skips the first two rows (headers and totals).

### 3. Local Development

```bash
# Clone or download the repository
# Navigate to the project directory

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

### 4. Deploy to Streamlit Cloud

1. Push your code to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Select your repository
5. Set main file path to `app.py`
6. Deploy!

The application will be available at your custom Streamlit URL.

## Usage

1. **Enter API Key**: Input your YouTube API key in the sidebar
2. **Upload CSV**: Upload your YouTube Analytics CSV file
3. **View Analysis**: Browse videos organized by time periods with:
   - Video thumbnails
   - Clickable titles (open in new tab)
   - Average view duration
   - Impressions and CTR
   - View counts
   - Watch time

## Data Sources

- **CSV File**: Impressions, CTR, average view duration, watch time
- **YouTube API**: Video titles, thumbnails, publication dates, current view counts

## Requirements

- Python 3.7+
- Streamlit 1.28.0+
- pandas 2.0.0+
- requests 2.31.0+
- Valid YouTube Data API v3 key

## File Structure

```
├── app.py              # Main Streamlit application
├── youtube_analyzer.py # YouTube API wrapper with caching
├── ui.py              # UI components and styling
├── utils.py           # Utility functions
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## Recent Improvements (v2.0)

### Code Quality & Architecture
- **Modular Design**: Split monolithic code into focused modules
- **Type Safety**: Added comprehensive type hints throughout
- **Error Handling**: Robust error handling with user-friendly messages
- **Logging**: Added structured logging for debugging

### Performance Optimizations
- **Caching**: Added Streamlit caching for API calls and data processing
- **Rate Limiting**: Intelligent API rate limiting with exponential backoff
- **Batch Processing**: Efficient batch processing of large datasets
- **Memory Management**: Optimized memory usage for large CSV files

### User Experience Enhancements
- **Enhanced Progress Tracking**: Real-time progress with detailed status updates
- **Better Error Messages**: Clear, actionable error messages with help text
- **File Validation**: Comprehensive CSV validation with format guidance
- **Processing Summary**: Detailed summary of processing results
- **Data Export**: Option to download processed data as CSV
- **Responsive UI**: Improved mobile and desktop experience

### Technical Improvements
- **Session Management**: Better handling of API sessions
- **Input Validation**: Comprehensive validation of all inputs
- **Encoding Support**: Support for multiple CSV encodings (UTF-8, Latin-1)
- **Duplicate Handling**: Smart handling of duplicate video IDs
- **API Resilience**: Retry logic for failed API calls

## Troubleshooting

- **API Quota Exceeded**: YouTube API has daily quotas. Monitor usage in Google Cloud Console.
- **Invalid Video IDs**: Ensure CSV contains proper YT_RELATED.{video_id} format.
- **Missing Data**: Some videos may not return data if they're private or deleted.

## Support

For issues or questions, please check:
1. YouTube API key is valid and has proper permissions
2. CSV file format matches expected structure
3. Video IDs in CSV are accessible via YouTube API
