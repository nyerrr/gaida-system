# GAIDA Test Credentials

## Temporary Test Accounts for Development

Use these credentials to test the login flow. These are valid until removed.

### Test Account 1
- **Student Number:** `2024001`
- **UE Email:** `student1@ue.edu.ph`
- **Access Code:** `ACCESS123`
- **Antibot Validation:** `HELLO`

### Test Account 2
- **Student Number:** `2024002`
- **UE Email:** `student2@ue.edu.ph`
- **Access Code:** `ACCESS456`
- **Antibot Validation:** `WORLD`

### Test Account 3
- **Student Number:** `2024003`
- **UE Email:** `student3@ue.edu.ph`
- **Access Code:** `ACCESS789`
- **Antibot Validation:** `GAIDA`

## How to Use

1. **Start the Backend Server**
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```
   The backend will run on `http://localhost:8000`

2. **Start the Frontend Server**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Login with Test Credentials**
   - Navigate to the Student Login page
   - Enter any of the test account details above
   - Click "Log In"
   - You will be redirected to the ConsentForm page

## Available Endpoints

- **Login:** `POST /api/auth/login`
  - Request body:
    ```json
    {
      "student_number": "2024001",
      "email": "student1@ue.edu.ph",
      "access_code": "ACCESS123",
      "antibot": "HELLO"
    }
    ```

- **Get Test Credentials** (for reference): `GET /api/auth/test-credentials`
  - Returns all available test accounts

## Notes

- ⚠️ **REMOVE THIS ENDPOINT IN PRODUCTION!** Remove the `get_test_credentials()` endpoint before deploying.
- The session token is stored in `localStorage` as `session_token`
- The student ID is stored in `localStorage` as `student_id`
- All credentials are case-sensitive
