int main() {
  int a = 1;
  {
    a = a + 2;
    int a = 3;
    a = a + 4;
  }
  a = a + 5;
  return a;
}
