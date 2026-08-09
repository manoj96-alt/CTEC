import { browserAuthConfig } from "@/lib/auth/config";
test("browser auth configuration fails closed", () => {
  expect(() => browserAuthConfig()).toThrow("configuration is incomplete");
});
