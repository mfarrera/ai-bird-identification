import { test, expect } from '@playwright/test'

test('la pantalla de login se muestra', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('Inici de sessió').first()).toBeVisible()
  await expect(page.locator('input[type="email"]')).toBeVisible()
  await expect(page.locator('input[type="password"]')).toBeVisible()
})

test('credenciales incorrectas muestran un error', async ({ page }) => {
  await page.goto('/')
  await page.locator('input[type="email"]').fill('no-existe@example.com')
  await page.locator('input[type="password"]').fill('contrasenya-incorrecta')
  await page.getByRole('button', { name: 'Iniciar sessió' }).click()

  await expect(page.locator('.alert-error')).toBeVisible()
  await expect(page).toHaveURL('/') // no ha navegado a ningún sitio
})
