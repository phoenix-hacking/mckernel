long m15_named_global = 0x13579bdfL;
int m15_named_function(int x) { return x + (int)m15_named_global; }
int main(void) { return m15_named_function(1) == 0; }
