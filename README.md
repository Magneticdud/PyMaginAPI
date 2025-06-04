# PyMaginAPI: the Pixabay Image App

A Python Tkinter application for searching and browsing images from Pixabay. Features a responsive grid layout and easy image ID copying.

![The project icon](icon.png)

This is a simple application that allows users to search for images using keywords and browse through the results in a responsive grid layout. The application also allows users to copy the ID of any image to their clipboard with a single click. Why just copy the ID instead of downloading the image or making it larger? Because I use the ID to download the image using the Pixabay API in a different program, this is just a quick and easy way to get the ID of the image you want instead of using the browser.

## Features

- Search for images using keywords
- Display results in a 4-column grid
- View image details including ID, tags, and photographer
- Copy image ID to clipboard with a single click
- Scrollable interface

## Prerequisites

- Python 3.6 or higher
- Pip (Python package installer)

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd PyMaginAPI
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your Pixabay API key:
   - Get your API key from [Pixabay API Documentation](https://pixabay.com/api/docs/) (requires login)
   - Create a `.env` file in the project root
   - Add your API key to the `.env` file:
     ```
     PIXABAY_API_KEY=your_api_key_here
     ```

## Usage

Run the application:
```bash
python pixabay_viewer.py
```

## Controls

- **Search**: Enter keywords in the search bar and press Enter or click the Search button
- **Copy ID**: Click on any image's ID to copy it to your clipboard
- **Scroll**: Use the scrollbar or mouse wheel to browse through search results

## Example .env File

Create a `.env` file based on the provided `.env.example`:
```
PIXABAY_API_KEY=your_api_key_here
```

## Note

- The application requires an active internet connection to fetch images
- The free tier of Pixabay API has rate limits (100 requests per hour)
- Never share your API key or commit it to version control

## License

[GPL-3.0](LICENSE)
