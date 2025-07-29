# Expense Tracker Frontend

A modern React-based web application for expense tracking and budget management.

## Features

- **Authentication**: Secure login and registration with JWT tokens
- **Dashboard**: Overview of expenses, budgets, and financial insights
- **Expense Management**: Add, edit, delete, and categorize expenses
- **Budget Tracking**: Create and monitor budgets with alerts
- **Analytics**: Visual charts and spending analysis
- **Statement Import**: Upload and parse bank statements
- **Real-time Updates**: WebSocket integration for live updates
- **Responsive Design**: Mobile-friendly interface using Tailwind CSS

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **React Router** for navigation
- **Tailwind CSS** for styling
- **Shadcn/ui** for UI components
- **Recharts** for data visualization
- **React Hook Form** with Zod validation
- **Vitest** for testing
- **React Testing Library** for component testing

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API server running (see backend README)

### Installation

1. Clone the repository and navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Copy environment variables:
```bash
cp .env.example .env
```

4. Update the `.env` file with your configuration:
```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws
```

### Development

Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Building for Production

Build the application:
```bash
npm run build
```

Preview the production build:
```bash
npm run preview
```

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── ui/             # Shadcn/ui components
│   ├── Layout.tsx      # Main layout wrapper
│   ├── ExpenseForm.tsx # Expense creation/editing form
│   └── ...
├── contexts/           # React contexts
│   ├── AuthContext.tsx # Authentication state
│   └── WebSocketContext.tsx # WebSocket connection
├── hooks/              # Custom React hooks
├── lib/                # Utility libraries
│   ├── api.ts          # API client
│   ├── utils.ts        # Helper functions
│   └── supabase.ts     # Supabase client (if used)
├── pages/              # Page components
│   ├── Dashboard.tsx   # Main dashboard
│   ├── Expenses.tsx    # Expense management
│   ├── Budgets.tsx     # Budget management
│   ├── Analytics.tsx   # Analytics and reports
│   ├── Login.tsx       # Authentication
│   └── ...
├── test/               # Test files
└── types/              # TypeScript type definitions
```

## Key Components

### Authentication
- JWT-based authentication with automatic token refresh
- Protected routes that redirect to login
- User context for managing authentication state

### API Integration
- Centralized API client with error handling
- Automatic token attachment to requests
- Type-safe API calls with TypeScript

### Real-time Features
- WebSocket integration for live updates
- Real-time expense notifications
- Live budget alerts and progress updates

### Form Handling
- React Hook Form with Zod validation
- Reusable form components
- Client-side validation with server-side error handling

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run test` - Run tests once
- `npm run test:watch` - Run tests in watch mode
- `npm run test:ui` - Run tests with UI
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix ESLint issues
- `npm run type-check` - Run TypeScript type checking

## Testing

The project uses Vitest and React Testing Library for testing:

```bash
# Run all tests
npm run test

# Run tests in watch mode
npm run test:watch

# Run tests with UI
npm run test:ui
```

### Test Structure
- Unit tests for components and utilities
- Integration tests for user workflows
- Mock implementations for external dependencies

## Styling

The application uses Tailwind CSS with a custom design system:

- **Colors**: Primary, secondary, accent colors defined in CSS variables
- **Components**: Shadcn/ui components for consistent styling
- **Responsive**: Mobile-first responsive design
- **Dark Mode**: Support for light/dark theme switching

## State Management

- **React Context**: For global state (auth, WebSocket)
- **Local State**: useState and useReducer for component state
- **Server State**: API client handles caching and synchronization

## Performance Optimizations

- **Code Splitting**: Lazy loading of routes and components
- **Bundle Optimization**: Vite's built-in optimizations
- **Image Optimization**: Proper image formats and lazy loading
- **Memoization**: React.memo and useMemo where appropriate

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Deployment

### Static Hosting (Recommended)
1. Build the application: `npm run build`
2. Deploy the `dist` folder to your hosting provider
3. Configure your web server to serve `index.html` for all routes

### Docker
```dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000/api/v1` |
| `VITE_WS_URL` | WebSocket URL | `ws://localhost:8000/ws` |
| `VITE_SUPABASE_URL` | Supabase project URL | - |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous key | - |

## Contributing

1. Follow the existing code style and conventions
2. Write tests for new features and bug fixes
3. Update documentation as needed
4. Use conventional commit messages
5. Ensure all tests pass before submitting

## Troubleshooting

### Common Issues

**Build fails with TypeScript errors:**
- Run `npm run type-check` to see detailed errors
- Ensure all dependencies are properly typed

**API requests fail:**
- Check that the backend server is running
- Verify the `VITE_API_URL` environment variable
- Check browser network tab for detailed error messages

**WebSocket connection fails:**
- Ensure the WebSocket server is running
- Check the `VITE_WS_URL` environment variable
- Verify firewall settings allow WebSocket connections

**Tests fail:**
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Update test snapshots if needed: `npm run test -- -u`

### Development Tips

- Use React Developer Tools for debugging
- Enable source maps in development for better debugging
- Use the network tab to monitor API requests
- Check console for any JavaScript errors

## License

This project is part of the Expense Tracker application suite.